from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_OCR_BYTES", str(512 * 1024 * 1024)))
WORK_DIR = Path(os.environ.get("WORK_DIR", "/work"))
OCR_TIMEOUT = int(os.environ.get("OCR_TIMEOUT_SECONDS", "1200"))
OCR_LANGUAGE = os.environ.get("OCR_LANGUAGE", "deu+eng")
job_lock = threading.Lock()


@app.get("/health")
def health():
    commands = ("ocrmypdf", "tesseract")
    missing = [command for command in commands if shutil.which(command) is None]
    if missing:
        return jsonify(ok=False, error="Missing OCR tools: " + ", ".join(missing)), 503
    return jsonify(ok=True)


@app.post("/api/ocr")
def ocr():
    if not job_lock.acquire(blocking=False):
        return jsonify(ok=False, error="Text recognition is busy. Please try again shortly."), 409
    temporary = None
    try:
        upload = request.files.get("file")
        if upload is None or not upload.filename.lower().endswith(".pdf"):
            return jsonify(ok=False, error="A PDF file is required."), 422
        temporary = tempfile.TemporaryDirectory(prefix="ocr-", dir=WORK_DIR)
        root = Path(temporary.name)
        source = root / "input.pdf"
        target = root / "output.pdf"
        upload.save(source)
        if source.stat().st_size < 5 or b"%PDF-" not in source.read_bytes()[:1024]:
            return jsonify(ok=False, error="The uploaded file is not a valid PDF."), 422
        command = [
            "ocrmypdf",
            "--language", OCR_LANGUAGE,
            "--deskew",
            "--rotate-pages",
            "--optimize", "1",
            "--skip-text",
            "--output-type", "pdf",
            str(source),
            str(target),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=OCR_TIMEOUT,
            env={**os.environ, "TMPDIR": str(root)},
        )
        if result.returncode != 0 or not target.exists():
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            app.logger.error("OCRmyPDF failed with code %s: %s", result.returncode, detail[-1] if detail else "no detail")
            return jsonify(ok=False, error="Text recognition could not process this PDF."), 422
        response = send_file(
            target,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="searchable.pdf",
            conditional=False,
        )
        response.call_on_close(temporary.cleanup)
        temporary = None
        return response
    except subprocess.TimeoutExpired:
        return jsonify(ok=False, error="Text recognition took too long and was stopped."), 504
    except OSError:
        app.logger.exception("OCR job failed")
        return jsonify(ok=False, error="Text recognition encountered a system error."), 500
    finally:
        if temporary is not None:
            temporary.cleanup()
        job_lock.release()


@app.errorhandler(413)
def too_large(_error):
    return jsonify(ok=False, error="The PDF is too large for text recognition."), 413
