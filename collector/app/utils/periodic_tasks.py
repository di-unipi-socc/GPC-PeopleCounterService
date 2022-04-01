import time
from datetime import datetime, timedelta

from apscheduler.triggers.date import DateTrigger
from flask import Flask
from flask_apscheduler import APScheduler
from flask_apscheduler.auth import HTTPBasicAuth

from db.db_mismatch import MismatchRecord
from endpoints.queries_utils import estimate_people_num, estimate_people_now_custom, estimate_people_evts, gen_evt_strings, \
    get_next_closedays_set, cleanup_all_db, get_accuracy_mismatch_based
from net_io.mail_management import MailManager
from db.db_base import Session

from configs.config import NOW_TIMERANGE, ALL_STR, H_DAILY_REPORT, H_NIGHT_REPORT, NIGHT_TIMERANGE, \
    email_anomal_activities_recipients, WEEK_CLOSE_DAYS, INST_ALERT_REFRESH_RATE, INST_ALERT_TRIGGER_P_NUM, \
    INST_ALERT_RENEW_RANGE_H, USERS, USERS_PASS, DB_CLEAN_DAYS_BEFORE, DB_NEXT_CLEAN_DAYS, \
    ACCURACY_DAYS


def is_close_night_weekend(dt_now):
    """
    Utility function that establish if given datetime is inside a night or weekend time-range
    :param dt_now:
    :return: True if dt_now is inside night or weekend time-range; False otherwise.
    """
    dt_now = dt_now.replace(microsecond=0)
    dt_1 = dt_now.replace(hour=NIGHT_TIMERANGE[0], minute=0, second=0)
    if dt_now < dt_1:
        dt_1 -= timedelta(days=1)
    dt_2 = dt_1.replace(hour=NIGHT_TIMERANGE[1]) + timedelta(days=1)
    if dt_1 <= dt_now <= dt_2:
        return True
    if dt_now.weekday() in WEEK_CLOSE_DAYS:
        return True
    return False


def get_close_range(dt_from: datetime):
    """
    Perform a query to DB to retrieve all closing days from a given datetime to next 60 days, and establish
    the closing time-range of building, from the same datetime.
    :param dt_from:
    :return: datetime Tuple: (start_close_day, end_close_day)
    """
    session = Session()
    next_closedays = get_next_closedays_set(dt_from.date(), 60, session)
    session.close()

    if not is_close_night_weekend(dt_from) and dt_from.date() not in next_closedays:
        dt_from = dt_from.replace(hour=NIGHT_TIMERANGE[0], minute=0, second=0, microsecond=0)
    close = [dt_from, dt_from.replace(hour=NIGHT_TIMERANGE[1], minute=0, second=0, microsecond=0)]
    if close[1] <= close[0]:
        close[1] = close[1] + timedelta(days=1)
    dt_next = close[1] + timedelta(minutes=1)

    while is_close_night_weekend(dt_next) or dt_next.date() in next_closedays:
        dt_next += timedelta(days=1)
        close[1] = dt_next.replace(minute=0)

    return close[0], close[1]


def is_close_date(dt_now: datetime):
    """
    :param dt_now:
    :return: True if `dt_now` is a close-day, False otherwise
    """
    if dt_now.weekday() in WEEK_CLOSE_DAYS:
        return True
    session = Session()
    next_closedays = get_next_closedays_set(dt_now.date(), 60, session)
    session.close()
    if dt_now.date() in next_closedays:
        return True


def was_night_range(r_start: datetime, r_end: datetime):
    """
    Establish if given time-range is a Night-Range or not
    :param r_start:
    :param r_end:
    :return: True if time-range is a Night-Range, False otherwise
    """
    assert r_start <= r_end
    dt_now = datetime.now().replace(microsecond=0)
    night_start = dt_now.replace(hour=NIGHT_TIMERANGE[0], minute=0, second=0)
    if dt_now < night_start:
        night_start -= timedelta(days=1)
    night_end = night_start.replace(hour=NIGHT_TIMERANGE[1]) + timedelta(days=1)

    night_range_delta = night_end - night_start
    range_delta = r_end - r_start

    is_night_range = range_delta <= night_range_delta
    return is_night_range


def setup_periodic_tasks(app: Flask, mail_man: MailManager):
    """
    Setup function that attach APScheduler to the given FlaskApp
    :param app: FlaskApp
    :param mail_man: MailManager object
    :return: APScheduler instance
    """
    class Config:
        """App configuration."""
        SCHEDULER_API_ENABLED = True
        SCHEDULER_AUTH = HTTPBasicAuth()

    scheduler = APScheduler()
    app.config.from_object(Config())

    mail_man.scheduler = scheduler

    @scheduler.task(id='daily_mismatch', name='MismatchReport', max_instances=1, misfire_grace_time=None,
                    trigger='cron', hour=H_DAILY_REPORT)
    def daily_report_mismatch():
        """
        Task for add new mismatch record to insert to the DB.
        Also send an email to report the obtained mismatch result, and update current self-evaluated accuracy.
        After his execution, it re-schedule itself for next day.
        :return:
        """
        h_range_ls = {NOW_TIMERANGE[0], NOW_TIMERANGE[1]}
        h_range_ls = sorted(h_range_ls)
        session = Session()
        mismatches = {}
        dt_now = datetime.now() - timedelta(days=1)
        for h_reset in h_range_ls:
            dt_reset = dt_now.replace(hour=h_reset, minute=0, second=0, microsecond=0)
            dt_reset += timedelta(seconds=1)
            if dt_reset > dt_reset:
                dt_reset -= timedelta(days=1)
            res = estimate_people_now_custom(ALL_STR, dt_reset, session)

            mismatch = MismatchRecord(datetime.now().timestamp(), res['in'], res['out'], res['tot'])
            session.add(mismatch)

            if res['tot'] != 0:
                mismatches[str(dt_reset.replace(microsecond=0))] = res
        session.commit()

        app.config['ACCURACY'] = get_accuracy_mismatch_based(ACCURACY_DAYS, session)

        session.close()

        if len(mismatches) > 0:
            msg = f'Daily Report performed @ {datetime.now().replace(microsecond=0)}\n\n'
            for h_reset in mismatches:
                msg += f'Mismatches for Reset after {h_reset}:\n'
                msg += str(mismatches[h_reset]) + '\n'
                msg += '\n'
            mail_man.broadcast_alert_email('Daily Mismatch Report', msg)
            with app.app_context():
                app.logger.info('Daily Mismatch Report sent')

    @scheduler.task(id='daily_night_rep', name='NightReport', max_instances=1, misfire_grace_time=None,
                    trigger='cron', hour=H_NIGHT_REPORT)  # minute=50
    def daily_report_night():
        """
        Perform, in a working days, a daily time-range query for the last night-range period, and send an email to report all
        Entrances/Exits events.
        :return:
        """
        try:
            if is_close_date(datetime.now()) or is_close_date(datetime.now()-timedelta(days=1)):
                with app.app_context():
                    app.logger.info('Night Activity Report Skip for close-day')
                return
            session = Session()
            dt_now = datetime.now() - timedelta(days=1)
            dt_1 = dt_now.replace(hour=NIGHT_TIMERANGE[0], minute=0, second=0, microsecond=0)
            dt_2 = dt_1.replace(hour=NIGHT_TIMERANGE[1]) + timedelta(days=1)
            evts_ls = estimate_people_evts(ALL_STR, dt_1, dt_2, False, session)
            session.close()

            evts_str_ls = gen_evt_strings(evts_ls)

            msg = 'Night report: '
            msg += f'{str(dt_1.replace(microsecond=0))} --- {str(dt_2.replace(microsecond=0))}\n'
            if len(evts_str_ls) > 0:
                for e_str in evts_str_ls:
                    msg += f'\t{e_str}\n'
            else:
                msg += 'Nothing to Report\n'
            mail_man.broadcast_user_email(email_anomal_activities_recipients, 'Night Activity Report', msg)
            # mail_man.broadcast_user_email(email_anomal_activities_recipients,
            #                               'Night Activity Report DELAYED', msg, datetime.now().replace(minute=15))
            with app.app_context():
                app.logger.info('Anomalous Night Activity mail sent')
        except Exception as e:
            with app.app_context():
                app.logger.error(f'Daily Night Report Failure:\n{str(e)}')

    dt_start, _ = get_close_range(datetime.now())
    with app.app_context():
        app.logger.info(f'Instant Alert task will turned on @ {dt_start.replace(microsecond=0)}')

    @scheduler.task(id='inst_alert', name='InstantAlert', max_instances=1, misfire_grace_time=None,
                    trigger='date', run_date=dt_start)
    def instant_alert():
        """
        Task activated during closing time-ranges, and send an email if catch some Entrances/Exits Events.
        At the end of his execution, send an email that report all entrances/exit events in closing time-range,
        and re-schedule itself.
        :return:
        """
        dt_start0, dt_end0 = get_close_range(datetime.now())

        dt_start, dt_end = dt_start0.replace(), dt_end0.replace()

        while dt_start <= datetime.now() < dt_end:
            try:
                time.sleep(INST_ALERT_REFRESH_RATE)
                session = Session()
                cnts = estimate_people_num(ALL_STR, dt_start, dt_end, False, session)
                session.close()
                assert len(cnts) == 1
                _, p_in, p_out = cnts[0]

                if (p_in - p_out) >= INST_ALERT_TRIGGER_P_NUM:
                    msg = f'Someone in the building:\n'
                    msg += f'\tDetected {p_in - p_out} Persons in the building in time-rage '
                    msg += f'{dt_start.replace(microsecond=0)} --- {datetime.now().replace(microsecond=0)}\n\n'
                    session = Session()
                    cnt_now = estimate_people_now_custom(ALL_STR, datetime.now(), session)
                    session.close()
                    msg += f'Total people estimated today: {cnt_now["tot"]}\n\n'
                    msg += f'For further information, please inspect the Event List\n'
                    mail_man.broadcast_user_email(email_anomal_activities_recipients,
                                                  'Anomalous Activity in Close Time', msg)
                    with app.app_context():
                        app.logger.info('Instant Alert mail sent')
                    dt_start = datetime.now()

                if p_in < p_out:
                    dt_start = datetime.now()
                elif datetime.now() - dt_start > timedelta(hours=INST_ALERT_RENEW_RANGE_H):
                    dt_start = datetime.now() - timedelta(hours=INST_ALERT_RENEW_RANGE_H)

            except Exception as e:
                with app.app_context():
                    app.logger.error(f'Something wrong during Instant Alert task: \n{str(e)}')

        try:
            if not was_night_range(dt_start0, dt_end0):
                session = Session()
                evts_ls = estimate_people_evts(ALL_STR, dt_start0, dt_end0, False, session)
                session.close()
                evts_str_ls = gen_evt_strings(evts_ls)
                msg = f'Activity during Close Time:'
                msg += f'{str(dt_start0.replace(microsecond=0))} --- {str(dt_end0.replace(microsecond=0))}\n'
                if len(evts_str_ls) > 0:
                    for e_str in evts_str_ls:
                        msg += f'\t{e_str}\n'
                else:
                    msg += 'Nothing to Report'
                send_date = datetime.now().replace(hour=H_NIGHT_REPORT, minute=0, second=0, microsecond=0)
                if send_date < datetime.now():
                    send_date = None
                mail_man.broadcast_user_email(email_anomal_activities_recipients,
                                              '[Recap] Activity in Closing Time', msg, send_date)
                with app.app_context():
                    app.logger.info('Recap Anomalous Close Activity mail sent')
        except Exception as e:
            with app.app_context():
                app.logger.error(f'Something wrong during Instant Alert task (Recap Email): \n{str(e)}')

        dt_next_close, _ = get_close_range(datetime.now())
        j = scheduler.add_job(id='inst_alert', name='InstantAlert', func=instant_alert,
                              max_instances=1, misfire_grace_time=None,
                              trigger=DateTrigger(run_date=dt_next_close))
        with app.app_context():
            app.logger.info(f'Instant Alert task will turned on @ {dt_next_close.replace(microsecond=0)}')

    dt_clean = datetime.now() + timedelta(minutes=5)

    @scheduler.task(id='clean_db', name='CleanupDB', max_instances=1, misfire_grace_time=None, trigger='date', run_date=dt_clean)
    def cleanup_db():
        """
        Cleanup Record DB function. Remove all records older than a given date
        :return:
        """
        last_valid_dt = datetime.now() - timedelta(days=DB_CLEAN_DAYS_BEFORE)
        session = None
        try:
            session = Session()
            results = cleanup_all_db(last_valid_dt, session)
            msg = f'Cleanup DB DONE!\nDelete all records older than {str(last_valid_dt.replace(microsecond=0))}\n'
            msg += '\tResults:\n'
            for k in results:
                msg += f'\t\t- {k}: {results[k]}\n'
            mail_man.broadcast_alert_email('Cleanup DB Report', msg)
            with app.app_context():
                app.logger.info(msg)
        except Exception as e:
            if session:
                session.rollback()
            msg = f'[{str(datetime.now().replace(microsecond=0))}]Something wrong during Cleanup DB:\n{str(e)}'
            with app.app_context():
                app.logger.error(msg)
            try:
                mail_man.broadcast_alert_email('[ALERT] Cleanup DB ERROR!', msg)
            except:
                pass
        finally:
            if session:
                session.close()

        dt_next_clean = datetime.now().replace(hour=NOW_TIMERANGE[0], minute=0, second=0, microsecond=0)
        dt_next_clean += timedelta(days=DB_NEXT_CLEAN_DAYS)
        dt_next_clean -= timedelta(minutes=10)
        scheduler.add_job(id='clean_db', name='CleanupDB', func=cleanup_db,
                          max_instances=1, misfire_grace_time=None,
                          trigger=DateTrigger(run_date=dt_next_clean))

    @scheduler.authenticate
    def authenticate(auth):
        """Check auth."""
        return auth["username"] == USERS[0] and auth["password"] == USERS_PASS[0]

    scheduler.init_app(app)
    scheduler.start()
    return scheduler