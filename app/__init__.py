import logging
from pathlib import Path

from flask import Flask, render_template

from config import Config

from .extensions import csrf, db
from .services.document_service import DocumentPrintService
from .services.image_service import ImageService
from .services.label_print_service import LabelPrintService
from .services.scan_file_service import ScanFileService
from .services.scanner_client import ScannerClient
from .services.template_service import TemplateService


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object:
        app.config.from_object(config_object)

    db.init_app(app)
    csrf.init_app(app)

    Path(app.config["JOBS_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["SCANS_DIR"]).mkdir(parents=True, exist_ok=True)

    app.extensions["template_service"] = TemplateService(
        app.config["LABEL_TEMPLATE_DIR"]
    )
    app.extensions["image_service"] = ImageService(
        max_bytes=20 * 1024 * 1024,
        max_pixels=app.config["IMAGE_MAX_PIXELS"],
        output_dpi=app.config["LABEL_IMAGE_DPI"],
    )
    app.extensions["label_print_service"] = LabelPrintService(
        printer_name=app.config["DYMO_PRINTER_NAME"],
        cups_server=app.config["CUPS_SERVER"],
        timeout_seconds=app.config["PRINT_TIMEOUT_SECONDS"],
        max_copies=app.config["MAX_COPIES"],
        landscape_offset_mm=app.config["DYMO_LANDSCAPE_OFFSET_MM"],
        landscape_shrink_mm=app.config["DYMO_LANDSCAPE_SHRINK_MM"],
        landscape_start_trim_mm=app.config["DYMO_LANDSCAPE_START_TRIM_MM"],
    )
    app.extensions["document_print_service"] = DocumentPrintService(
        jobs_dir=app.config["JOBS_DIR"],
        config_path=app.config["PRINTER_CONFIG"],
        cups_server=app.config["CUPS_SERVER"],
    )
    app.extensions["scanner_client"] = ScannerClient(
        app.config["SCANNER_URL"], app.config["SCANNER_TIMEOUT_SECONDS"]
    )
    app.extensions["scan_file_service"] = ScanFileService(
        app.config["SCANS_DIR"]
    )

    from .routes.documents import bp as documents_bp
    from .routes.home import bp as home_bp
    from .routes.labels import bp as labels_bp
    from .routes.printing import bp as printing_bp
    from .routes.scans import bp as scans_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(labels_bp)
    app.register_blueprint(printing_bp)
    app.register_blueprint(scans_bp)

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; "
            "style-src 'self'; script-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
            "form-action 'self'",
        )
        return response

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "errors/error.html",
            title="Not found",
            message="The requested page could not be found.",
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Unhandled application error", exc_info=error)
        return render_template(
            "errors/error.html",
            title="Something went wrong",
            message="Please try again later.",
        ), 500

    with app.app_context():
        db.create_all()

    if not app.debug:
        logging.getLogger("werkzeug").setLevel(logging.INFO)
    return app
