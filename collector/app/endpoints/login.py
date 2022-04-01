import datetime

import flask
from flask import Flask, redirect, url_for, render_template, request, abort
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user, \
    AnonymousUserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Length
from configs.config import app_secret_key, SQLALCHEMY_DATABASE_URI


def login_setup(app: Flask):
    """
    Attach and setup all configurations of Login System
    :param app:
    :return: db and User class, used to store and represent the Users logged to the app
    """
    app: Flask

    @app.before_request
    def before_request():
        """
        Reset the current Session timeout and check User logged in
        :return:
        """
        r = request
        if not current_user.is_authenticated and not request.endpoint == 'login':
            redirect('/login')
        else:
            flask.session.permanent = True
            app.permanent_session_lifetime = datetime.timedelta(minutes=30)
            flask.session.modified = True

    # Set the configs for User DB
    app.config['SECRET_KEY'] = app_secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    bootstrap = Bootstrap(app)
    db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    class User(UserMixin, db.Model):
        """
        ORM Class that represent a Collector User, containing all needed information to login
        """
        __tablename__ = 'user'
        id = db.Column(db.Integer, primary_key=True, autoincrement=True)
        email = db.Column(db.Unicode(128), nullable=False)
        username = db.Column(db.Unicode(32), nullable=False, unique=True)
        password = db.Column(db.Unicode(128), nullable=False)
        is_active = db.Column(db.Boolean, default=True)
        is_admin = db.Column(db.Boolean, default=False)
        # is_anonymous = False
        # authenticated = False

        def __init__(self, *args, **kw):
            super(User, self).__init__(*args, **kw)

        def set_password(self, password):
            self.password = generate_password_hash(password)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.request_loader
    def load_user_from_header(param):
        auth = request.authorization
        if not auth:
            return None
        user = User.query.filter_by(username=auth.username).first()
        if not user or not check_password_hash(user.password, auth.password):
            abort(401)
        return user

    class LoginForm(FlaskForm):
        """
        Wrap-Class containing all login fields
        """
        username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
        password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
        remember = BooleanField('remember me')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """
        Endpoint for offer login-form and gather the result
        :return:
        """
        form = LoginForm()

        dest = request.args.get('next')

        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user:
                if check_password_hash(user.password, form.password.data):
                    login_user(user, remember=form.remember.data)
                    user.authenticated = True
                    # with app.app_context():
                    app.logger.warning(f'Login: User {user.username} access to the GUI at {datetime.datetime.now()}')
                    if dest:
                        return redirect(dest)
                    return redirect('/')

            return '<h1>Invalid username or password</h1>'

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        """
        Endpoint to perform Logout, and invalidate current login-session
        :return:
        """
        logout_user()
        redir_str = '/'
        return redirect(redir_str)

    return db, User

