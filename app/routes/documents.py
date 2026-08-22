from flask import Blueprint, current_app, jsonify, render_template, request

from ..services.document_service import DocumentPrintError


bp = Blueprint("documents", __name__, url_prefix="/documents")


def service():
    return current_app.extensions["document_print_service"]


@bp.get("")
def index():
    return render_template("documents/index.html")


@bp.get("/api/status")
def status():
    try:
        return jsonify(ok=True, **service().status())
    except DocumentPrintError as exc:
        return jsonify(ok=False, error=str(exc)), 503


@bp.post("/api/print-jobs")
def print_jobs():
    try:
        payload = request.get_json(silent=True) or {}
        count = service().print_files(str(payload.get("printer", "")), service().pdf_jobs())
        return jsonify(ok=True, printed=count)
    except DocumentPrintError as exc:
        return jsonify(ok=False, error=str(exc)), 422


@bp.post("/api/print-pdf")
def print_pdf():
    try:
        path = service().save_upload(
            request.args.get("filename", "Document.pdf"), request.get_data()
        )
        try:
            count = service().print_files(request.args.get("printer", ""), [path])
        except Exception as exc:
            raise DocumentPrintError(f"{exc} The PDF remains in the jobs folder.") from exc
        return jsonify(ok=True, printed=count)
    except DocumentPrintError as exc:
        return jsonify(ok=False, error=str(exc)), 422

