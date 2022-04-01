import os
from datetime import datetime

from apscheduler.triggers.date import DateTrigger
from flask import Flask
from flask_apscheduler import APScheduler
from flask_mail import Mail, Message

from configs.config import email_pass, email_addr, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL, \
    DISABLE_ENABLE_URL

DEBUG = bool(os.getenv('DEBUG'))


class MailManager:
    """
    API Class that contain all methods to interact with Email Server
    """
    def __init__(self, app: Flask, user_class, alert_recipients=None, scheduler: APScheduler = None):
        """
        :param app: Target FlaskApp
        :param user_class: User Class to interact with User DB
        :param alert_recipients: Username-List of all user interested on alert mails
        :param scheduler: APScheduler object, used to postpone email's send
        """
        if alert_recipients is None:
            alert_recipients = []
        self.scheduler = scheduler
        app.config['MAIL_SERVER'] = MAIL_SERVER
        app.config['MAIL_PORT'] = MAIL_PORT
        app.config['MAIL_USERNAME'] = email_addr
        app.config['MAIL_PASSWORD'] = email_pass
        app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
        app.config['MAIL_USE_SSL'] = MAIL_USE_SSL

        self.sender = app.config['MAIL_USERNAME']
        app.config['MAIL_DEFAULT_SENDER'] = self.sender

        self.app = app
        self.mail = Mail(app)
        self.User = user_class
        self.alert_user_ls = alert_recipients

        self.no_disturb_users = set()

        if DEBUG:
            with app.app_context():
                app.logger.warning(f'env var DEBUG={DEBUG}, EMAIL SEND DISABLED!')

    def send_1_email(self, dest, subj, body, date: datetime = None):
        """
        Send an Email forwarding the request to email Server via SMTP
        :param dest: destination email address
        :param subj:
        :param body:
        :param date: datetime object to specify postpone send action
        :return:
        """
        if date and self.scheduler:
            tim = date.timestamp()
            j = self.scheduler.add_job(id=f'delay_mail_{tim}', name=f'DelayedMail-{tim}',
                                       func=lambda: self.send_1_email(dest, subj, body),
                                       trigger=DateTrigger(run_date=date))
            return
        with self.app.app_context():
            msg = Message(subj, sender=self.sender, recipients=[dest])
            msg.body = body
            if not DEBUG:
                self.mail.send(msg)

    def broadcast_alert_email(self, subj, body):
        self.broadcast_user_email(self.alert_user_ls, subj, body)

    def broadcast_user_email(self, user_ls, subj, body, date: datetime = None):
        """
        Broadcast an email to each user in `user_ls` (if username is not in no-disturb-list)
        :param user_ls: List of usernames
        :param subj:
        :param body:
        :param date: datetime object to specify postpone send action
        :return:
        """
        dest_set = set()
        for username in user_ls:
            user = self.User.query.filter_by(username=username).first()
            if user and username not in self.no_disturb_users:
                dest_set.add(user.email)
        self.broadcast_email(list(dest_set), subj, body, date)

    def broadcast_email(self, dest_ls, subj, body, date: datetime = None):
        """
        Send an email to each address in `dest_ls` list
        :param dest_ls: List of email addresses
        :param subj:
        :param body:
        :param date: datetime object to specify postpone send action
        :return:
        """
        if len(dest_ls) < 1:
            return
        if date and self.scheduler:
            tim = date.timestamp()
            j = self.scheduler.add_job(id=f'delay_mail_{tim}', name=f'DelayedMail-{tim}',
                                       func=lambda: self.broadcast_email(dest_ls, subj, body),
                                       trigger=DateTrigger(run_date=date))
            return

        with self.app.app_context():
            body = self.__add_disable_info_footer__(body)
            with self.mail.connect() as conn:
                for dst in dest_ls:
                    message = body
                    subject = subj
                    msg = Message(recipients=[dst],
                                  body=message,
                                  subject=subject)
                    if not DEBUG:
                        conn.send(msg)

    def __add_disable_info_footer__(self, body):
        dis_enable_url = DISABLE_ENABLE_URL
        body += '\n______________________________________________________________________________\n'
        body += f'\tTo Disable this emails, follow this link: {dis_enable_url}/off \n'
        body += '______________________________________________________________________________\n'
        # body += f'To Re-Enable this emails, follow this link: {dis_enable_url}/on \n'
        return body

    def disable_user_email(self, username):
        """
        Add username string in `no-disturb` list, and no email will be broadcasted to him.
        :param username:
        :return:
        """
        self.no_disturb_users.add(username)

    def reactivate_user_email(self, username):
        """
        Remove username from `no-disturb list`
        :param username:
        :return:
        """
        if username in self.no_disturb_users:
            self.no_disturb_users.remove(username)


def setup_mail_manager(app: Flask, user_class, alert_recipients=None):
    """
    Utility function used to setup Mail manager object
    :param app: FlaskApp
    :param user_class: ORM User Class
    :param alert_recipients: List of username interested to receive alert emails
    :return: MailManager instance
    """
    if alert_recipients is None:
        alert_recipients = []
    manager = MailManager(app, user_class, alert_recipients)

    return manager
