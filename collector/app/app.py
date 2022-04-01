import json
import logging
import os
import time
from datetime import datetime, timedelta, date
from threading import Thread

import cv2
from flask import Flask, render_template, send_from_directory, request, Response, redirect, stream_with_context
from flask_basicauth import BasicAuth

import urllib3
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from endpoints.mail_set_form import UserModForm
from endpoints.queries_utils import get_next_closedays_set, cleanup_range_closedays, \
    get_accuracy_mismatch_based
from endpoints.closedays_form import CloseDaysForm
from db.db_closedays import CloseDayRecord
from utils.periodic_tasks import setup_periodic_tasks
from net_io.messages_websoc import MSGManagerThreadBody
from endpoints.unauth_check import is_unauthorized
from net_io.mail_management import MailManager, setup_mail_manager
from utils.frames_dict import FramesDict
from endpoints.login import login_setup
from utils.status import GlobalStatus
from net_io.mucounts import MUCounts
from endpoints.queries_ep import add_queries_ep
from net_io.updates_websoc import UpdateManagerThreadBody
from endpoints.reset_form_utils import ResetForm
from utils.status_manager import StatusManagerThreadBody

import configs.config as conf
from net_io.videostream_websoc import VideoGatherThreadBody
from db.db_base import Session

from db.db_init import create_all_tables

create_all_tables()

urllib3.disable_warnings(urllib3.exceptions.SecurityWarning)

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BASIC_AUTH_USERNAME'] = conf.auth_server[0]
app.config['BASIC_AUTH_PASSWORD'] = conf.auth_server[1]
basic_auth = BasicAuth(app)

# Setup Message Broadcast Thread
msg_man: MSGManagerThreadBody = MSGManagerThreadBody(conf.ssl_cert, conf.ssl_key)

# Frames collector for all Monitoring Units
fr_dict = FramesDict()

db_users, User = login_setup(app)

mail_manager: MailManager = setup_mail_manager(app, User, conf.email_alert_recipients)

app.config['ALL_UNITS'] = conf.ALL_UNITS
app.config['NOW_TIMERANGE'] = conf.NOW_TIMERANGE

status_manager: StatusManagerThreadBody = StatusManagerThreadBody(app, fr_dict, mail_manager, msg_man)

update_manager: UpdateManagerThreadBody = add_queries_ep(app, status_manager)

glob_stat = GlobalStatus(update_manager, status_manager)

scheduler = setup_periodic_tasks(app, mail_manager)

refresh_triggers = set()
refresh_triggers.add('/')

app.config['VIDEO_SRCS'] = fr_dict

app.config['VIDEO_ENABLE'] = conf.VIDEO_ENABLE_LS
app.config['QRY_CNT_ENABLE'] = conf.QRY_CNT_ENABLE_LS
app.config['QRY_EVT_ENABLE'] = conf.QRY_EVT_ENABLE_LS
app.config['QRY_DEV_ENABLE'] = conf.QRY_DEV_ENABLE_LS
app.config['RESET_ENABLE'] = conf.RESET_ENABLE_LS
app.config['CLOSE_DAYS_ENABLE'] = conf.CLOSE_DAYS_ENABLE_LS
app.config['UPDATE_ENABLE'] = conf.UPDATE_ENABLE_LS
app.config['EMAIL_USER_ENABLE'] = conf.EMAIL_USER_ENABLE
app.config['MANAGE_USERS_ENABLE'] = conf.MANAGE_USERS_ENABLE_LS

session = Session()
app.config['ACCURACY'] = get_accuracy_mismatch_based(conf.ACCURACY_DAYS, session)
session.close()


@app.before_request
def refresh_broadcasted_counts():
    # Refresh "broadcast counts" (UpdateManager.init_update)
    if request.path in refresh_triggers:
        # app.logger.info(f"UPDATE by: '{request.path}'")
        try:
            glob_stat.broadcast_counts()
        except Exception as e:
            with app.app_context():
                app.logger.error(str(e))


@app.route('/')
@login_required
def index():
    user = current_user.username
    return render_template('mainpage.html', online_mu=status_manager.get_online_devices())


@app.route('/cam_view/<id>', methods=['GET'])
@login_required
def cam_view(id):
    """
    Provide rendered GUI-View to a single MU debug frames-stream
    :param id:
    :return:
    """
    if is_unauthorized('VIDEO_ENABLE', app):
        return redirect('/unauthorized')
    return render_template('cam_view.html', device=id)


@app.route('/update', methods=['POST'])
@login_required
def update_status():
    """
    Endpoint exploited from MUs to send Counts Estimations updates
    :return:
    """
    if is_unauthorized('UPDATE_ENABLE', app):
        return 'unautorized to send update', 401
    try:
        status_j = json.loads(request.data)
    except Exception as e:
        # with app.app_context():
        app.logger.error(str(e) + '\n' + str(request.data))
        return 'Fail to parse JSON', 400

    mu_update = None
    try:
        mu_update = MUCounts(status_j)
    except Exception as e:
        # with app.app_context():
        app.logger.error(str(e))
        return 'MUCounts(status_j)' + str(e), 400

    try:
        glob_stat.update_count(mu_update)
    except Exception as e:
        # with app.app_context():
        app.logger.error(str(e))
        return 'glob_stat.update_count(mu_update)' + str(e), 400

    return 'ACK', 200


refresh_triggers.add('/reset_form')


@app.route('/reset_form', methods=['GET', 'POST'])
@login_required
def reset_form_fn():
    """
    GUI-view used to add a new reset record
    :return:
    """
    if is_unauthorized('RESET_ENABLE', app):
        return redirect('/unauthorized')
    form = ResetForm()
    msg = ''

    if form.validate_on_submit():
        session = Session()

        try:
            glob_stat.reset_counters(form)
            msg = f'Counters reset correctly'
            glob_stat.broadcast_counts()
        except Exception as e:
            # TODO: Manage Failures
            # return str(e), 400
            return render_template('reset.html', form=form, msg=str(e))
        finally:
            session.close()
        return render_template('reset.html', form=form, msg=msg)

    form.time.data = datetime.now()

    return render_template('reset.html', form=form, msg=msg)


def closedays_to_display(session):
    """
    Utility function to retrieve closing days to view on GUI
    :param session:
    :return:
    """
    day_from = datetime.today() - timedelta(days=conf.CLOSE_DAYS_DISPLAY_RANGE[0])
    close_days = get_next_closedays_set(day_from, conf.CLOSE_DAYS_DISPLAY_RANGE[1], session)
    close_days = list(close_days)
    close_days.sort()
    return close_days


@app.route('/close_days_form', methods=['GET', 'POST'])
@login_required
def closedays_form_fn():
    """
    Endpoint that offer GUI interface to Add/Remove close days record
    :return:
    """
    if is_unauthorized('CLOSE_DAYS_ENABLE', app):
        return redirect('/unauthorized')
    form: CloseDaysForm = CloseDaysForm()
    msg = 'Insert Day (or Days-Range)'

    session = Session()
    close_days = []
    try:
        close_days = closedays_to_display(session)
    except Exception as e:
        session.close()
        msg = str(e)
        # msg = 'Error on gathering Closing days to display'
        return render_template('close_days.html', form=form, msg=msg, closedays=close_days)

    if form.validate_on_submit():
        try:
            if form.cleanup_range.data:
                assert form.date1.data <= form.date2.data, "WRONG time-range to delete"
                cleanup_range_closedays(form.date1.data, form.date2.data, session)
                msg = 'Cleanup Range Closed-Days Done'
            else:
                # if form.date1.data <= form.date2.data:
                if date.today() < form.date1.data <= form.date2.data:
                    day = form.date1.data
                    while day <= form.date2.data:
                        session.add(CloseDayRecord(day))
                        day += timedelta(days=1)
                    session.commit()
                    msg = f'Day(s) Added Correctly'
                elif date.today() < form.date1.data:
                    session.add(CloseDayRecord(form.date1.data))
                    session.commit()
                    msg = f'Single Day Added Correctly'
                else:
                    msg = f'[!] Should be: "{date.today()}" < "{form.date1.label.text}" <= "{form.date2.label.text}" '

            close_days = closedays_to_display(session)
        except IntegrityError:
            session.rollback()
            session.close()
            msg = "Error: Day/Days-Range overlapping with already closing-days registered"
        except Exception as e:
            session.rollback()
            session.close()
            # TODO: Manage Failures
            # return str(e), 400
            return render_template('close_days.html', form=form, msg=str(e), closedays=close_days)

    session.close()

    form.date1.data = datetime.today()
    form.date2.data = datetime.today()

    return render_template('close_days.html', form=form, msg=msg, closedays=close_days)


@app.route('/user_management', methods=['GET', 'POST'])
@login_required
def emails_manage_fn():
    """
    Endpoint that provide GUI-View to change User's Email
    :return:
    """
    if is_unauthorized('MANAGE_USERS_ENABLE', app):
        return redirect('/unauthorized')
    form = UserModForm()
    msg = 'Select an User and set an email'
    usr_email_ls = []

    session = db_users.session()

    if form.validate_on_submit():
        username = form.username.data
        try:
            user = session.query(User).filter_by(username=username).first()
            if user:
                msg = f'[{username}] '
                if len(form.email.data) > 5:
                    user.email = form.email.data
                    # session.add(user)
                    msg += f' Set "{form.email.data}"'
                if len(form.password.data) > 8:
                    user.set_password(form.password.data)
                    # session.add(user)
                    msg += f' Reset Password'
                session.commit()
            else:
                msg = f'User "{username}" NOT valid'
        except Exception as e:
            msg = str(e)
        # finally:
        #     session.close()

    try:
        usr_ls = session.query(User).all()
        for user in usr_ls:
            usr_email_ls.append((user.username, user.email))
    except Exception as e:
        msg = str(e)

    session.close()

    return render_template('user_management.html', form=form, msg=msg, usr_email_ls=usr_email_ls)


def stream_frame(img):
    """
    Utility function used to format byte string to be sent to Client's GUI
    :param img:
    :return:
    """
    res, buf = cv2.imencode('.jpg', img)
    frame = buf.tobytes()
    return (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/videogate/local/<id>', methods=['GET'])
@login_required
def stream_video_local(id):
    """
    Endpoint that offer debug video-stream of one/more MUs
    :param id:
    :return:
    """
    if is_unauthorized('VIDEO_ENABLE', app):
        return 'unauthorized', 401
    if id == 'all':
        def gen():
            img = fr_dict.get_all_frames(2)
            while img is not None:
                t_send = time.time()
                yield stream_frame(img)
                img = fr_dict.get_all_frames(2)
                if (time.time() - t_send) < (1 / 10):
                    time.sleep(1 / 10)
                    # print('.', end='')

    elif not (id in fr_dict.get_streamers()):
        return 'Camera Offline', 404
        # return send_from_directory(os.path.join(app.root_path, 'static'),
        #                            'offline.gif', mimetype='image/gif')
    else:
        def gen():
            try:
                img = fr_dict.get_frame(id)
                while img is not None:
                    yield stream_frame(img)
                    img_prev = img
                    img = fr_dict.get_frame_no_duplicate(id, img_prev)
                    n_try = int(10 * conf.MU_IS_ALIVE_T / 2)
                    while img is None:
                        time.sleep(1 / 10)
                        n_try -= 1
                        if n_try < 0:
                            raise Exception('Is the same frame for too long')
                        img = fr_dict.get_frame_no_duplicate(id, img_prev)
            except Exception as e:
                with app.app_context():
                    app.logger.error(str(e))
            return None

    try:
        return Response(stream_with_context(gen()),
                        mimetype='multipart/x-mixed-replace; boundary=frame',
                        headers={'Cache-Control': 'no-cache'})
    except:
        pass
    return 'End Stream', 404


@app.route('/email/<on_off>', methods=['GET'])
@login_required
def on_off_email(on_off):
    """
    Endpoint to enable/disable emails send to logged current user
    :param on_off:
    :return:
    """
    user = current_user.username
    if on_off == 'on':
        mail_manager.reactivate_user_email(user)
    elif on_off == 'off':
        mail_manager.disable_user_email(user)
    elif on_off == 'status':
        pass
    else:
        return f"Invalid option {on_off}", 500

    email_enabled = user not in mail_manager.no_disturb_users
    return render_template('enable_disable_email.html', is_enable=email_enabled)


@app.route('/accuracy', methods=['GET'])
@login_required
def accuracy_ep():
    accuracy = json.dumps(app.config['ACCURACY'])
    return accuracy, 200


@app.before_first_request
def init_setup():
    """
    Setup and start Collectors threads
    :return:
    """
    gatherer = VideoGatherThreadBody(f_dict=fr_dict, cert_file=conf.ssl_cert, key_file=conf.ssl_key)
    th_gather = Thread(target=gatherer)
    th_gather.start()

    th_status_manager = Thread(target=status_manager)
    th_status_manager.start()

    th_msg_man = Thread(target=msg_man)
    th_msg_man.start()

    boot_time = datetime.now().replace(microsecond=0)
    mail_manager.broadcast_alert_email(f'GIO-Counter: START', f'Server reboot @ {str(boot_time)}')

    with app.app_context():
        app.logger.setLevel(logging.INFO)
        app.logger.info('SETUP COMPLETE')

    app.logger.info('Server Start')


@app.route('/unauthorized')
@login_required
def unauth_ep():
    return render_template('unatuhorized_access.html'), 401


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'static/favicon.ico', mimetype='image/x-icon')


if __name__ == '__main__':
    # standalone https run
    app.run(debug=True, host='0.0.0.0', ssl_context=("static/ssl/cert.pem", 'static/ssl/key.pem'))

    # with Haproxy redirect
    # app.run(debug=True, host='0.0.0.0')
