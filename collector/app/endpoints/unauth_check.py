from flask import Flask
from flask_login import current_user


def is_unauthorized(area, app: Flask):
    """
    Check if current user is authorized to access to that resources
    :param area: String TAG of resources
    :param app:
    :return: True if the current user in UN-Authorized
    """
    is_authenticated = current_user.is_authenticated
    if is_authenticated:
        return current_user.username not in app.config[area]
    else:
        return True
