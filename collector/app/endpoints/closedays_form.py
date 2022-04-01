from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms.fields import DateField
from wtforms.validators import InputRequired


class CloseDaysForm(FlaskForm):
    """
    Wrap-Class containing insert/delete closing day(s) range
    """
    cleanup_range = BooleanField('Cleanup Range', default=False)
    date1 = DateField('Day from', validators=[InputRequired()], format='%Y-%m-%d', default=datetime.today())
    date2 = DateField('Day to', validators=[InputRequired()], format='%Y-%m-%d', default=datetime.today())

