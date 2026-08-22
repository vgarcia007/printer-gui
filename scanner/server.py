from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import img2pdf
import requests
from flask import Flask, jsonify, request
from PIL import Image, ImageStat


app = Flask(__name__)
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
WORK_DIR = Path(os.environ.get("WORK_DIR", "/work"))
STATE_DIR = Path(os.environ.get("STATE_DIR", "/state"))
SCANS_DIR = Path(os.environ.get("SCANS_DIR", "/scans"))
OCR_URL = os.environ.get("OCR_URL", "http://ocr:8080/api/ocr")
OCR_TIMEOUT = int(os.environ.get("OCR_TIMEOUT_SECONDS", "1200"))
SCAN_TIMEOUT = int(os.environ.get("SCAN_TIMEOUT_SECONDS", "600"))
BLANK_INK_FRACTION = float(os.environ.get("BLANK_INK_FRACTION", "0.0015"))

state_lock = threading.RLock()
process_lock = threading.RLock()
current_process: subprocess.Popen | None = None
cancel_requested = threading.Event()
state: dict[str, object] = {"state": "idle", "jobId": None}


def set_state(**values) -> dict[str, object]:
    with state_lock:
        state.update(values)
        return dict(state)


def get_state() -> dict[str, object]:
    with state_lock:
        return dict(state)


def fail(message: str, *, retry: bool = False, filename: str | None = None) -> None:
    set_state(state="error", error=message, retryAvailable=retry, filename=filename)


def job_root(job_id: str) -> Path:
    return WORK_DIR / ("scan-" + job_id)


def page_files(job_id: str, side: str) -> list[Path]:
    return sorted(job_root(job_id).glob(side + "-*.pnm"))


def cleanup_job(job_id: str | None) -> None:
    if job_id:
        shutil.rmtree(job_root(job_id), ignore_errors=True)


def cleanup_stale_partials() -> None:
    SCANS_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now().timestamp() - timedelta(hours=24).total_seconds()
    for path in SCANS_DIR.glob(".partial-*"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            app.logger.warning("Could not remove stale partial file %s", path)


def is_blank(path: Path) -> bool:
    with Image.open(path) as source:
        gray = source.convert("L")
        gray.thumbnail((700, 1000))
        histogram = gray.histogram()
        pixels = max(1, gray.width * gray.height)
        dark_pixels = sum(histogram[:235])
        very_dark = sum(histogram[:200])
        return dark_pixels / pixels < BLANK_INK_FRACTION and very_dark / pixels < 0.0004


def filtered_pages(paths: list[Path]) -> list[Path]:
    kept = [path for path in paths if not is_blank(path)]
    return kept or paths[:1]


def run_scan(job_id: str, side: str, mode: str) -> list[Path]:
    root = job_root(job_id)
    root.mkdir(parents=True, exist_ok=True)
    scan_mode = "24bit Color[Fast]" if mode == "color" else "True Gray"
    pattern = str(root / (side + "-%04d.pnm"))
    command = [
        "scanimage",
        "-l", "0", "-t", "0", "-x", "215", "-y", "297",
        "--source", "Automatic Document Feeder(left aligned)",
        "--mode", scan_mode,
        "--resolution", "150",
        "--format=pnm",
        "--batch=" + pattern,
    ]
    global current_process
    with process_lock:
        if cancel_requested.is_set():
            raise RuntimeError("The scan was cancelled.")
        current_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process = current_process
    try:
        stdout, stderr = process.communicate(timeout=SCAN_TIMEOUT)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        raise RuntimeError("The scanner took too long and was stopped.")
    finally:
        with process_lock:
            if current_process is process:
                current_process = None
    pages = page_files(job_id, side)
    if cancel_requested.is_set():
        raise RuntimeError("The scan was cancelled.")
    if not pages:
        detail = (stderr or stdout or "").strip().splitlines()
        app.logger.error("scanimage failed (%s): %s", process.returncode, detail[-1] if detail else "no output")
        raise RuntimeError("No pages were scanned. Check the feeder and try again.")
    return pages


def ordered_pages(job_id: str, duplex: bool) -> list[Path]:
    fronts = filtered_pages(page_files(job_id, "front"))
    if not duplex:
        return fronts
    backs = filtered_pages(page_files(job_id, "back"))
    if len(fronts) != len(backs):
        raise RuntimeError("The number of front and back pages does not match. Please start the scan again.")
    ordered: list[Path] = []
    for front, back in zip(fronts, reversed(backs)):
        ordered.extend((front, back))
    return ordered


def create_pdf(paths: list[Path], target: Path) -> None:
    if not paths:
        raise RuntimeError("No non-blank pages were found.")
    with target.open("wb") as output:
        output.write(img2pdf.convert([str(path) for path in paths]))


def atomic_copy(source: Path, filename: str) -> Path:
    SCANS_DIR.mkdir(parents=True, exist_ok=True)
    destination = SCANS_DIR / filename
    if destination.exists():
        stem = destination.stem
        counter = 2
        while destination.exists():
            destination = SCANS_DIR / (stem + "-" + str(counter) + ".pdf")
            counter += 1
    temporary = SCANS_DIR / (".partial-" + uuid.uuid4().hex)
    try:
        with source.open("rb") as incoming, temporary.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def submit_ocr(source: Path, target: Path) -> None:
    with source.open("rb") as stream:
        response = requests.post(
            OCR_URL,
            files={"file": (source.name, stream, "application/pdf")},
            timeout=(10, OCR_TIMEOUT),
            stream=True,
        )
        if response.status_code != 200:
            try:
                message = response.json().get("error")
            except ValueError:
                message = None
            raise RuntimeError(message or "Text recognition is unavailable.")
        with target.open("xb") as output:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    if target.stat().st_size < 5 or b"%PDF-" not in target.read_bytes()[:1024]:
        target.unlink(missing_ok=True)
        raise RuntimeError("Text recognition returned an invalid PDF.")


def finish_job(job_id: str, duplex: bool) -> None:
    root = job_root(job_id)
    raw = root / "raw.pdf"
    ocr_output = root / "searchable.pdf"
    try:
        set_state(state="processing", error=None, retryAvailable=False)
        create_pdf(ordered_pages(job_id, duplex), raw)
        if cancel_requested.is_set():
            raise RuntimeError("The scan was cancelled.")
        try:
            submit_ocr(raw, ocr_output)
        except Exception as exc:
            stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            rescue = atomic_copy(raw, stamp + "-ocr-failed.pdf")
            fail(
                "The pages were scanned, but text recognition failed. The original PDF was kept.",
                retry=True,
                filename=rescue.name,
            )
            app.logger.warning("OCR failed: %s", exc)
            cleanup_job(job_id)
            return
        stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        final = atomic_copy(ocr_output, stamp + ".pdf")
        set_state(state="done", filename=final.name, error=None, retryAvailable=False)
        cleanup_job(job_id)
    except Exception as exc:
        if cancel_requested.is_set():
            set_state(state="idle", jobId=None, error=None, retryAvailable=False, filename=None)
        else:
            fail(str(exc))
            app.logger.exception("Scan processing failed")
        cleanup_job(job_id)


def scan_front_worker(job_id: str, mode: str) -> None:
    try:
        run_scan(job_id, "front", mode)
        if not cancel_requested.is_set():
            set_state(state="awaiting_decision")
    except Exception as exc:
        if cancel_requested.is_set():
            set_state(state="idle", jobId=None, error=None, retryAvailable=False)
        else:
            fail(str(exc))
            app.logger.exception("Front scan failed")
        cleanup_job(job_id)


def scan_back_worker(job_id: str, mode: str) -> None:
    try:
        run_scan(job_id, "back", mode)
        finish_job(job_id, True)
    except Exception as exc:
        if cancel_requested.is_set():
            set_state(state="idle", jobId=None, error=None, retryAvailable=False)
        else:
            fail(str(exc))
            app.logger.exception("Back scan failed")
        cleanup_job(job_id)


def retry_worker(job_id: str, filename: str) -> None:
    root = job_root(job_id)
    root.mkdir(parents=True, exist_ok=True)
    source = SCANS_DIR / filename
    output = root / "retry-searchable.pdf"
    try:
        set_state(state="processing", error=None, retryAvailable=False)
        submit_ocr(source, output)
        final_name = filename.removesuffix("-ocr-failed.pdf") + ".pdf"
        final = atomic_copy(output, final_name)
        source.unlink(missing_ok=True)
        set_state(state="done", filename=final.name, error=None, retryAvailable=False)
        cleanup_job(job_id)
    except Exception as exc:
        fail("Text recognition failed again. The original PDF is still available.", retry=True, filename=filename)
        app.logger.warning("OCR retry failed: %s", exc)
        cleanup_job(job_id)


def start_worker(target, *args) -> None:
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()


@app.get("/health")
def health():
    scanner = shutil.which("scanimage") is not None
    return jsonify(ok=scanner), (200 if scanner else 503)


@app.get("/status")
def status():
    return jsonify(get_state())


@app.post("/jobs")
def start_job():
    with state_lock:
        if state.get("state") not in {"idle", "done", "error", "cancelled"}:
            return jsonify(error="A scan is already in progress."), 409
        mode = (request.get_json(silent=True) or {}).get("mode", "document")
        if mode not in {"document", "color"}:
            return jsonify(error="Choose Document or Color mode."), 422
        cleanup_job(state.get("jobId"))
        job_id = uuid.uuid4().hex
        cancel_requested.clear()
        set_state(state="scanning_front", jobId=job_id, mode=mode, filename=None, error=None, retryAvailable=False)
    start_worker(scan_front_worker, job_id, mode)
    return jsonify(get_state()), 202


@app.post("/jobs/<job_id>/back")
def back(job_id: str):
    current = get_state()
    if current.get("jobId") != job_id or current.get("state") != "awaiting_decision":
        return jsonify(error="This scan is not waiting for back sides."), 409
    set_state(state="scanning_back")
    start_worker(scan_back_worker, job_id, str(current.get("mode", "document")))
    return jsonify(get_state()), 202


@app.post("/jobs/<job_id>/finish")
def finish(job_id: str):
    current = get_state()
    if current.get("jobId") != job_id or current.get("state") != "awaiting_decision":
        return jsonify(error="This scan is not ready to finish."), 409
    set_state(state="processing")
    start_worker(finish_job, job_id, False)
    return jsonify(get_state()), 202


@app.post("/jobs/<job_id>/retry-ocr")
def retry(job_id: str):
    current = get_state()
    filename = current.get("filename")
    if current.get("jobId") != job_id or not current.get("retryAvailable") or not isinstance(filename, str):
        return jsonify(error="Text recognition cannot be retried for this scan."), 409
    source = SCANS_DIR / filename
    if not source.is_file():
        return jsonify(error="The original PDF no longer exists."), 404
    start_worker(retry_worker, job_id, filename)
    return jsonify(get_state()), 202


@app.post("/jobs/<job_id>/cancel")
def cancel(job_id: str):
    current = get_state()
    if current.get("jobId") != job_id:
        return jsonify(error="This scan is no longer active."), 409
    cancel_requested.set()
    with process_lock:
        if current_process is not None and current_process.poll() is None:
            current_process.terminate()
    cleanup_job(job_id)
    set_state(state="idle", jobId=None, mode=None, filename=None, error=None, retryAvailable=False)
    return jsonify(get_state())


cleanup_stale_partials()
STATE_DIR.mkdir(parents=True, exist_ok=True)
