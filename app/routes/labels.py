from flask import Blueprint, Response, abort, current_app, flash, jsonify, redirect, render_template, request, url_for

from ..extensions import db
from ..forms import ComposeLabelForm, DeleteForm, PrintLabelForm
from ..models import Label
from ..services.editor_document import EditorDocumentError, sanitize_editor_document
from ..services.image_service import ImageValidationError


bp = Blueprint("labels", __name__, url_prefix="/labels")


def saved_label_list() -> list[Label]:
    return db.session.execute(
        db.select(Label)
        .where(Label.is_saved.is_(True), Label.source_type == "editor")
        .order_by(Label.updated_at.desc())
    ).scalars().all()


def render_editor(label=None, copy=False):
    template = current_app.extensions["template_service"].all()[0]
    width_mm, height_mm = template.dimensions_for("landscape")
    image_service = current_app.extensions["image_service"]
    output_width, output_height = image_service.pixel_dimensions(width_mm, height_mm)
    return render_template(
        "labels/editor.html",
        form=ComposeLabelForm(),
        editor_label=None if copy else label,
        editor_content=label.editor_content if label else None,
        editor_mode="copy" if copy else "edit" if label else "new",
        template=template,
        width_mm=width_mm,
        height_mm=height_mm,
        output_width_px=output_width,
        output_height_px=output_height,
        saved_labels=saved_label_list(),
    )


@bp.get("")
def index():
    return render_editor()


@bp.get("/<int:label_id>/edit")
def edit(label_id):
    label = db.get_or_404(Label, label_id)
    if label.source_type != "editor" or not label.editor_content:
        abort(404)
    return render_editor(label)


@bp.get("/<int:label_id>/copy")
def copy(label_id):
    label = db.get_or_404(Label, label_id)
    if label.source_type != "editor" or not label.editor_content:
        abort(404)
    return render_editor(label, copy=True)


@bp.post("/compose")
@bp.post("/<int:label_id>/compose")
def compose(label_id=None):
    form = ComposeLabelForm()
    if not form.validate_on_submit():
        return jsonify(error="Please check the label content."), 422
    try:
        if form.editor_action.data not in {"preview", "save"}:
            raise EditorDocumentError("The editor action is invalid.")
        content = sanitize_editor_document(
            form.editor_content.data,
            max_length=current_app.config["EDITOR_CONTENT_MAX_LENGTH"],
        )
        raw_png = form.png_file.data.read()
        template = current_app.extensions["template_service"].all()[0]
        width_mm, height_mm = template.dimensions_for("landscape")
        png = current_app.extensions["image_service"].validate_and_normalize(
            raw_png, width_mm, height_mm
        )
        if label_id is None:
            label = Label(
                template_id=template.id,
                orientation="landscape",
                width_mm=width_mm,
                height_mm=height_mm,
                source_type="editor",
                is_saved=False,
            )
            db.session.add(label)
        else:
            label = db.get_or_404(Label, label_id)
            if label.source_type != "editor":
                abort(404)
        label.user_prompt = form.editor_text.data.strip() or "Image label"
        label.png_content = png
        label.editor_content = content
        label.is_saved = form.editor_action.data == "save" or label.is_saved
        db.session.commit()
    except (EditorDocumentError, ImageValidationError) as exc:
        return jsonify(error=str(exc)), 422
    if form.editor_action.data == "save":
        return jsonify(redirect_url=url_for("labels.gallery"))
    return jsonify(redirect_url=url_for("labels.preview", label_id=label.id))


@bp.get("/gallery")
def gallery():
    return render_template("labels/gallery.html", labels=saved_label_list(), gallery_kind="editor")


@bp.get("/<int:label_id>/preview")
def preview(label_id):
    label = db.get_or_404(Label, label_id)
    return render_template(
        "labels/preview.html",
        label=label,
        print_form=PrintLabelForm(),
        saved_labels=saved_label_list(),
    )


@bp.get("/<int:label_id>/preview.png")
def preview_png(label_id):
    label = db.get_or_404(Label, label_id)
    width = min(max(request.args.get("width", 1200, type=int), 240), 1600)
    png = current_app.extensions["image_service"].preview(label.png_content, width)
    response = Response(png, mimetype="image/png")
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@bp.post("/<int:label_id>/delete")
def delete(label_id):
    label = db.get_or_404(Label, label_id)
    if not DeleteForm().validate_on_submit() or not label.is_saved:
        flash("The label could not be deleted.", "danger")
    else:
        db.session.delete(label)
        db.session.commit()
        flash("The label was deleted.", "success")
    if request.form.get("return_to") == "editor":
        return redirect(url_for("labels.index"))
    return redirect(url_for("labels.gallery"))
