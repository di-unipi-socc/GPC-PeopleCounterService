from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms.fields import DateTimeField, IntegerField
from wtforms.validators import InputRequired

from configs.config import RESET_RECORD_NAME

RECORD_NAME = RESET_RECORD_NAME


class ResetForm(FlaskForm):
    """
    Wrap-Class containing all needed fields to add a Fix/Reset Counts Record
    """
    full = BooleanField('NOW', default=False)
    time = DateTimeField('Time', validators=[InputRequired()], format='%Y-%m-%dT%H:%M', default=datetime.now())
    entered = IntegerField('Entered', validators=[InputRequired()], default=0)
    exited = IntegerField('Exited', validators=[InputRequired()], default=0)
