import json
from datetime import datetime, timedelta
from threading import Thread

from flask import Flask, redirect, render_template
from flask_login import login_required
from utils.status_manager import StatusManagerThreadBody
from endpoints.unauth_check import is_unauthorized
from endpoints.queries_utils import FullFreeForm, estimate_people_num_form, estimate_people_evts_form, estimate_people_now, \
    gen_evt_strings, DeviceStatusForm, query_device_evts
from net_io.updates_websoc import UpdateManagerThreadBody

from configs.config import app_secret_key, ssl_key, ssl_cert, ALL_STR
from db.db_base import Session

# Base.metadata.create_all(engine)

ALL_ID = ALL_STR


def add_queries_ep(app: Flask, status_manager: StatusManagerThreadBody):
    """
    Define and add all DB-Interactions endpoints
    :param app: Target FlaskApp
    :param status_manager: Current object that contain all peripheral devices status
    :return:
    """
    app.config['SECRET_KEY'] = app_secret_key

    s = Session()
    counters = estimate_people_now(ALL_ID, s)
    s.close()
    update_0 = json.dumps(counters)

    # Setup Update manager object
    update_manager = UpdateManagerThreadBody(update_0, ssl_cert, ssl_key)

    @app.route('/qry_form_num', methods=['GET', 'POST'])
    @login_required
    def qry_form_num_fn():
        """
        Endpoint to perform Time-Range queries on Entrances/Exits Estimations, aggregated/each-gate
        :return:
        """
        if is_unauthorized('QRY_CNT_ENABLE', app):
            return redirect('/unauthorized')
        form = FullFreeForm()
        msg = ''
        p_counts = []

        if form.validate_on_submit():
            session = Session()

            try:
                p_counts = estimate_people_num_form(form, session)
                msg = f'People Counts Estimated:'
            except Exception as e:
                # TODO: Manage Failures
                # return str(e), 400
                msg = str(e)
            finally:
                session.close()

        if not form.validate_on_submit():
            form.time1.data = datetime.now() - timedelta(hours=1)
            form.time2.data = datetime.now() + timedelta(hours=1)

        return render_template('queries_counts.html',
                               form=form, msg=msg, cnt_ls=p_counts, dev_ls=status_manager.get_online_devices())

    @app.route('/qry_form_evt', methods=['GET', 'POST'])
    @login_required
    def qry_form_evt_fn():
        """
        Endpoint to perform Time-Range queries on Entrances/Exits Events for each/all gates
        :return:
        """
        if is_unauthorized('QRY_EVT_ENABLE', app):
            return redirect('/unauthorized')
        form = FullFreeForm()
        msg = ''
        evt_ls = []

        if form.validate_on_submit():
            session = Session()
            try:
                evt_ls = estimate_people_evts_form(form, session)
                evt_ls = gen_evt_strings(evt_ls)
                msg = f'Events detected'
            except Exception as e:
                # TODO: Manage Failures
                # return str(e), 400
                msg = str(e)
            finally:
                session.close()

        if not form.validate_on_submit():
            form.time1.data = datetime.now() - timedelta(hours=1)
            form.time2.data = datetime.now() + timedelta(hours=1)

        return render_template('queries_evts.html',
                               form=form, msg=msg, evt_ls=evt_ls, dev_ls=status_manager.get_online_devices())

    @app.route('/qry_form_dev_evt', methods=['GET', 'POST'])
    @login_required
    def qry_form_dev_evt_fn():
        """
        Endpoint to perform Time-Range queries on MonitorUnits Events: MU Connections/Disconnections.
        :return:
        """
        if is_unauthorized('QRY_DEV_ENABLE', app):
            return redirect('/unauthorized')
        form = DeviceStatusForm()
        msg = ''
        evt_ls = []

        if form.validate_on_submit():
            session = Session()
            try:
                evt_ls = query_device_evts(form, session)
                if len(evt_ls) > 0:
                    msg = f'Events Devices-Status detected'
                else:
                    msg = f'NO Info about {form.device.data} device'
            except Exception as e:
                # TODO: Manage Failures
                # return str(e), 400
                msg = str(e)
            finally:
                session.close()

        if not form.validate_on_submit():
            form.time1.data = datetime.now() - timedelta(hours=1)
            form.time2.data = datetime.now() + timedelta(hours=1)

        return render_template('queries_evts_dev.html',
                               form=form, msg=msg, evt_ls=evt_ls, dev_ls=status_manager.get_online_devices())

    @app.route('/qry_num_now/<id_gate>', methods=['GET'])
    @login_required
    def qry_num_now_fn(id_gate):
        """
        Utility Endpoint to retrieve current daily People Count Estimation
        :param id_gate: Gate's ID
        :return: Json containing Counts Estimations {'tot': x, 'in': y, 'out': z}
        """
        session = Session()

        counters = estimate_people_now(id_gate, session)

        session.close()

        json_string = json.dumps(counters)

        return json_string, 200

    # @app.route('/fake_update/', methods=['GET'])
    def fake_update_fn():
        """
        Disabled Mock Endpoint to test Broadcast Updates
        :return:
        """

        json_string, _ = qry_num_now_fn(ALL_ID)
        upd_dict = json.loads(json_string)
        update_manager.broadcast_update(upd_dict)
        return 'DONE!', 200

    @app.before_first_request
    def init_setup():
        """
        Create and put in Run-State the UpdateManager Thread
        :return:
        """
        th_update_manager = Thread(target=update_manager)
        th_update_manager.start()

    return update_manager
