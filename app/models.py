from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Label(db.Model):
    __tablename__ = "labels"

    id = db.Column(db.Integer, primary_key=True)
    user_prompt = db.Column(db.Text, nullable=False)
    template_id = db.Column(db.String(80), nullable=False, index=True)
    orientation = db.Column(db.String(20), nullable=False)
    width_mm = db.Column(db.Float, nullable=False)
    height_mm = db.Column(db.Float, nullable=False)
    png_content = db.Column(db.LargeBinary, nullable=False)
    source_type = db.Column(
        db.String(20), nullable=False, default="editor", index=True
    )
    editor_content = db.Column(db.Text, nullable=True)
    is_saved = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    def __repr__(self):
        return f"<Label {self.id}>"
