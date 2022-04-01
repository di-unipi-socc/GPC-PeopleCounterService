import os

from flask import Flask
from endpoints.login import login_setup

from configs.config import USERS, USERS_PASS, USERS_EMAIL, USER_DB_LOCATION

print(f'__name__ = {__name__}')
app = Flask(__name__)
db, User = login_setup(app)


def add_user(username, password, mail):
    user = User(username=username, email=mail)
    user.set_password(password)
    session = db.session()
    session.add(user)
    session.commit()
    session.close()


if __name__ == '__main__':
    if not os.path.exists(USER_DB_LOCATION):
        db.create_all(app=app)
        with app.app_context():
            assert len(USERS) == len(USERS_PASS) == len(USERS_EMAIL)
            for usr, psw, email in zip(USERS, USERS_PASS, USERS_EMAIL):
                add_user(usr, psw, email)
    else:
        with app.app_context():
            app.logger.warning("DB already exist")
