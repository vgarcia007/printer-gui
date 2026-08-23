from flask import Blueprint, current_app, flash, redirect, request, url_for

from ..extensions import db
from ..forms import PrintLabelForm
from ..i18n import gettext
from ..models import Label
from ..services.label_print_service import PrintError


bp = Blueprint("printing", __name__)


@bp.post("/labels/<int:label_id>/print")
def print_label(label_id):
    label = db.get_or_404(Label, label_id)
    form = PrintLabelForm()
    endpoint = "labels.gallery" if request.form.get("return_to") == "gallery" else "labels.preview"
    values = {} if endpoint == "labels.gallery" else {"label_id": label.id}
    if not form.validate_on_submit():
        flash(gettext("Choose between 1 and 100 copies."), "danger")
        return redirect(url_for(endpoint, **values))
    try:
        job_id = current_app.extensions["label_print_service"].print_png(
            label.png_content, label.width_mm, label.height_mm, form.copies.data
        )
    except PrintError as exc:
        flash(gettext(str(exc)), "danger")
    else:
        label.is_saved = True
        db.session.commit()
        flash(
            gettext("The label was sent to the printer ({job_id}).", job_id=job_id),
            "success",
        )
    return redirect(url_for(endpoint, **values))
