from flask import Blueprint, current_app, jsonify, render_template, request, send_file

from ..services.document_service import DocumentPrintError
from ..services.scan_file_service import ScanFileError
from ..services.scanner_client import ScannerClientError


bp = Blueprint("scans", __name__, url_prefix="/scans")


def scanner():
    return current_app.extensions["scanner_client"]


def files():
    return current_app.extensions["scan_file_service"]


def document_printer():
    return current_app.extensions["document_print_service"]


@bp.get("")
def index():
    return render_template("scans/index.html", scanner_model=current_app.config["SCANNER_MODEL"])


@bp.get("/files")
def file_page():
    return render_template("scans/files.html")


@bp.get("/api/status")
def status():
    try:
        return jsonify(ok=True, **scanner().status())
    except ScannerClientError as exc:
        return jsonify(ok=False, error=str(exc), state="error"), exc.status


@bp.post("/api/front")
def front():
    payload = request.get_json(silent=True) or {}
    return proxy_action("/jobs", {"mode": payload.get("mode")})


@bp.post("/api/<job_id>/<action>")
def job_action(job_id, action):
    if action not in {"back", "finish", "cancel", "retry-ocr"}:
        return jsonify(ok=False, error="Unknown scan action."), 404
    return proxy_action(f"/jobs/{job_id}/{action}")


def proxy_action(path, payload=None):
    try:
        return jsonify(ok=True, **scanner().action(path, payload))
    except ScannerClientError as exc:
        return jsonify(ok=False, error=str(exc)), exc.status


@bp.get("/api/files")
def file_list():
    return jsonify(ok=True, files=files().list())


@bp.get("/api/files/<path:filename>/download")
def download(filename):
    try:
        path = files().resolve(filename)
        return send_file(path, mimetype="application/pdf", as_attachment=True, download_name=path.name)
    except ScanFileError as exc:
        return jsonify(ok=False, error=str(exc)), exc.status


@bp.put("/api/files/<path:filename>")
def rename(filename):
    try:
        data = request.get_json(silent=True) or {}
        new_name = files().rename(filename, str(data.get("name", "")), str(data.get("prefix", "date")))
        return jsonify(ok=True, filename=new_name)
    except ScanFileError as exc:
        return jsonify(ok=False, error=str(exc)), exc.status


@bp.delete("/api/files/<path:filename>")
def delete(filename):
    try:
        files().delete(filename)
        return jsonify(ok=True)
    except ScanFileError as exc:
        return jsonify(ok=False, error=str(exc)), exc.status


@bp.post("/api/files/<path:filename>/print")
def print_file(filename):
    try:
        path = files().resolve(filename)
        payload = request.get_json(silent=True) or {}
        printer = str(payload.get("printer", ""))
        service = document_printer()
        label = service.print_preserved_pdf(printer, path)
        return jsonify(ok=True, message=f"The PDF was sent to {label}.")
    except ScanFileError as exc:
        return jsonify(ok=False, error=str(exc)), exc.status
    except DocumentPrintError as exc:
        return jsonify(ok=False, error=str(exc)), 422
