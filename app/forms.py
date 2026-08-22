from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import HiddenField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ComposeLabelForm(FlaskForm):
    editor_text = HiddenField(validators=[Optional(), Length(max=2000)])
    editor_content = HiddenField(validators=[DataRequired(), Length(max=6_000_000)])
    editor_action = HiddenField(validators=[DataRequired()])
    png_file = FileField(validators=[DataRequired()])
    submit = SubmitField("Continue to print")


class PrintLabelForm(FlaskForm):
    copies = IntegerField(
        "Copies", validators=[DataRequired(), NumberRange(min=1, max=100)], default=1
    )


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")

