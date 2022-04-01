from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length


class UserModForm(FlaskForm):
    """
    Wrap-Class containing all needed fields to modify user's informations
    """
    username = StringField('Username', validators=[InputRequired(), Length(min=3, max=15)])
    email = StringField('Email')  # validators=[InputRequired(), Length(min=3, max=80)]
    password = PasswordField('Password')
