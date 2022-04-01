from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.fields import DateTimeField
from wtforms.validators import InputRequired, Length
from datetime import datetime, timedelta, date
from sqlalchemy import func, and_

from db.people_count import PeopleCounts
from db.monitorunitstatus import MonitorUnitStatusRecord
from db.db_closedays import CloseDayRecord
from db.db_mismatch import MismatchRecord

from configs.config import NOW_TIMERANGE, ALL_STR


DEVICE_DEFAULT = ''
ALL = ALL_STR

class FullFreeForm(FlaskForm):
    """
    Wrap-Class containing all needed fields to perform Time-Range Queries
    """
    device = StringField('Device', validators=[Length(min=3, max=30)], default=DEVICE_DEFAULT)
    time1 = DateTimeField('Start', validators=[InputRequired()], format='%Y-%m-%dT%H:%M', default=datetime.now())
    time2 = DateTimeField('End', validators=[InputRequired()], format='%Y-%m-%dT%H:%M', default=datetime.now())
    per_gate = BooleanField('each_gate', default=False)


class DeviceStatusForm(FlaskForm):
    """
    Wrap-Class containing all fields to perform Time-Range queries on Device-Connections/Disconnections
    """
    device = StringField('Device', validators=[Length(min=3, max=30)], default=DEVICE_DEFAULT)
    time1 = DateTimeField('Time Start', validators=[InputRequired()], format='%Y-%m-%dT%H:%M',
                          default=datetime.now())
    time2 = DateTimeField('Time End', validators=[InputRequired()], format='%Y-%m-%dT%H:%M', default=datetime.now())


def estimate_people_num_form(form: FullFreeForm, session):
    """
    Wrap Function that retrieve form's fields and perform a time-range query on Counts Estimations
    :param form:
    :param session: Already initialised DB-session
    :return:
    """
    device_id = form.device.data
    dt_1 = form.time1.data
    dt_2 = form.time2.data
    to_group = form.per_gate.data

    return estimate_people_num(device_id, dt_1, dt_2, to_group, session)


def estimate_people_evts_form(form: FullFreeForm, session):
    """
    Wrap Function that retrieve form's fields and perform a time-range query on Enter/Exit Events
    :param form:
    :param session: Already initialised DB-session
    :return:
    """
    device_id = form.device.data
    dt_1 = form.time1.data
    dt_2 = form.time2.data
    to_group = form.per_gate.data

    return estimate_people_evts(device_id, dt_1, dt_2, to_group, session)


def query_device_evts(form: DeviceStatusForm, session):
    """
    Wrap Function that retrieve form's fields and perform a time-range query on MonitorUnits Connections/Disconnections
    :param form:
    :param session: Already initialised DB-session
    :return:
    """
    device_id = form.device.data
    dt_1 = form.time1.data
    dt_2 = form.time2.data

    return monitor_unit_evts(device_id, dt_1, dt_2, session)


def estimate_people_now(id_gate, session):
    """
    Utility Wrap Function, used to retrieve current daily Counts Estimations
    :param id_gate: Gate's ID
    :param session: Already initialised DB-session
    :return:
    """
    dt_now = datetime.now()
    return estimate_people_now_custom(id_gate, dt_now, session)


def estimate_people_now_custom(id_gate, dt_now, session):
    """
    Wrap-Function to perform Daily Counts Estimation
    :param id_gate: Gate's ID
    :param dt_now: DateTime object to be considered "Now" for the current query
    :param session: Already initialised DB-session
    :return:
    """

    # Define Time-Range of the query
    dt_r1 = dt_now.replace(hour=NOW_TIMERANGE[0], minute=0, second=0, microsecond=0)
    dt_r2 = dt_now.replace(hour=NOW_TIMERANGE[1], minute=0, second=0, microsecond=0)
    if dt_r2 <= dt_r1 < dt_now:
        dt_r2 += timedelta(days=1)
    elif dt_r2 <= dt_r1 and dt_now < dt_r1:
        dt_r1 -= timedelta(days=1)
    if dt_r1 <= dt_now <= dt_r2:
        dt_1 = dt_r1
        dt_2 = dt_r2
    else:
        if dt_now.hour >= NOW_TIMERANGE[1]:
            dt_r1 = dt_r1 + timedelta(days=1)
        else:
            dt_r2 = dt_r2 - timedelta(days=1)
        dt_1 = dt_r2
        dt_2 = dt_r1

    cnt_ls = estimate_people_num(id_gate, dt_1, dt_2, False, session)

    # Aggregate counts and build dict object containing counts estimations
    p_in, p_out, p_cnt = 0, 0, 0
    if len(cnt_ls) > 0:
        assert len(cnt_ls) == 1
        p_in, p_out = cnt_ls[0][1], cnt_ls[0][2]
        p_cnt = p_in - p_out

    return {'tot': p_cnt, 'in': p_in, 'out': p_out}


def estimate_people_num(device: str, time1: datetime, time2: datetime, per_gate: bool, session):
    """
    Function that performs the Time-Range Query for Counts Estimations.
    :param device: Device's ID
    :param time1: DateTime from
    :param time2: DateTime to
    :param per_gate: True=Keep Counts Estimation grouped by each gate
    :param session: Already initialised DB-session
    :return: Tuple-List containing Counts estimations (aggregated/each-gate). I.E.: [('gate_X', p_in, p_out), ('gate_Y'...]
    """
    qry = session.query(PeopleCounts.gate_id,
                        func.sum(PeopleCounts.entered).label("sum_in"),
                        func.sum(PeopleCounts.exited).label("sum_out")
                        )
    qry = qry.filter(
        and_(PeopleCounts.timestamp >= int(time1.timestamp()),
             PeopleCounts.timestamp <= int(time2.timestamp()))
    )

    if not (device == DEVICE_DEFAULT) and not (device == ALL):
        qry = qry.filter(PeopleCounts.gate_id == device)

    qry = qry.group_by(PeopleCounts.gate_id)

    res = qry.all()

    if ((device == DEVICE_DEFAULT) or (device == ALL)) and not per_gate:
        tot_in, tot_out = 0, 0
        for r in res:
            _, r_in, r_out = r
            tot_in += r_in
            tot_out += r_out
        return [('Aggregate Counts', tot_in, tot_out)]

    return res


def estimate_people_evts(device: str, time1: datetime, time2: datetime, per_gate: bool, session):
    """
    Function that performs the Time-Range Query for Counts Events.
    :param device: Device's ID
    :param time1: DateTime from
    :param time2: DateTime to
    :param per_gate: True=Keep Events grouped by each gate
    :param session: Already initialised DB-session
    :return: Tuple-List containing Counts estimations (aggregated/each-gate). I.E.: [('gate_X', p_in, p_out), ('gate_Y'...]
    """
    qry = session.query(PeopleCounts.gate_id,
                        PeopleCounts.timestamp,
                        func.sum(PeopleCounts.entered).label("sum_in"),
                        func.sum(PeopleCounts.exited).label("sum_out")
                        )
    qry = qry.filter(
        and_(PeopleCounts.timestamp >= int(time1.timestamp()),
             PeopleCounts.timestamp <= int(time2.timestamp()))
    )

    if not (device == DEVICE_DEFAULT) and not (device == ALL):
        qry = qry.filter(PeopleCounts.gate_id == device)

    if per_gate:
        qry = qry.group_by(PeopleCounts.gate_id, PeopleCounts.timestamp)
    else:
        qry = qry.group_by(PeopleCounts.timestamp, PeopleCounts.gate_id)

    qry = qry.order_by(PeopleCounts.timestamp)

    res = qry.all()

    return res


def gen_evt_strings(evts: list):
    """
    Utility function to create a formatted string containing readable informations about Counts Events
    :param evts: Events-List returned by `estimate_people_evts()` method
    :return: String-List
    """
    res_evts = []
    for e in evts:
        dt = datetime.fromtimestamp(int(e[1]))
        e_str = f'[{str(dt)}] from {e[0]}: '
        if e[2] != 0:
            e_str += f' {e[2]} person(s) Entered'
        if e[2] != 0 and e[3] != 0:
            e_str += ", "
        elif e[2] == 0 and e[3] == 0:
            e_str += "No Entrances or Exits"
        if e[3] != 0:
            e_str += f' {e[3]} person(s) Exited'
        e_str += '.'
        res_evts.append(e_str)
    return res_evts


def monitor_unit_evts(device: str, time1: datetime, time2: datetime, session):
    """
    Function that perform the time-range query on MonitorUnit Connection/Disconnection Events
    :param device: Device's ID / all_device string
    :param time1: DateTime from
    :param time2: DateTime to
    :param session: Already initialised DB-session
    :return: Tuple-List containing MU's Connection/Disconnection events
    """
    qry = session.query(MonitorUnitStatusRecord.gate_id,
                        MonitorUnitStatusRecord.timestamp,
                        MonitorUnitStatusRecord.msg,
                        )
    qry = qry.filter(
        and_(MonitorUnitStatusRecord.timestamp >= int(time1.timestamp()),
             MonitorUnitStatusRecord.timestamp <= int(time2.timestamp()))
    )

    if not (device == DEVICE_DEFAULT) and not (device == ALL):
        qry = qry.filter(MonitorUnitStatusRecord.gate_id == device)

    qry = qry.order_by(MonitorUnitStatusRecord.timestamp)

    _res = qry.all()
    res = []
    for r in _res:
        res.append((r[0], datetime.fromtimestamp(int(r[1])), r[2]))

    return res


def get_last_mismatches(past_days: int, session):
    """
    Function that perform last `past_days` mismatch records
    :param past_days: Last days to be considered
    :param session: Already initialised DB-session
    :return:
    """
    date_since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=past_days)
    qry = session.query(MismatchRecord)
    qry = qry.filter(MismatchRecord.timestamp >= date_since.timestamp())
    res = qry.all()

    return res


def get_next_closedays_set(from_day: date, next_range_days: int, session):
    """
    Function to perform query to retrieve all Closing Days fom a date to date+n
    :param from_day:
    :param next_range_days: Numer of days to consider in time-range query
    :param session: Already initialised DB-session
    :return: a set of Date objects that represents all Closing-Days retrieved from the query
    """
    qry = session.query(CloseDayRecord.day)
    closeday_max = from_day + timedelta(days=next_range_days)

    qry = qry.filter(
        and_(CloseDayRecord.day >= from_day,
             CloseDayRecord.day <= closeday_max)
    )
    res = qry.all()

    close_pool = set()
    for row in res:
        close_pool.add(row[0])

    return close_pool


def cleanup_older_closeday(from_day: date, session):
    """
    Utility function to delete all closing-day record older than `from_day` date
    :param from_day:
    :param session: Already initialised DB-session
    :return:
    """
    qry = session.query(CloseDayRecord)
    qry = qry.filter(CloseDayRecord.day < from_day)
    res = qry.all()

    for closeday in res:
        session.delete(closeday)
    session.commit()


def cleanup_range_closedays(from_day: date, to_day: date, session):
    """
    Function to remove all close-days record in a given time-range
    :param from_day:
    :param to_day:
    :param session: Already initialised DB-session
    :return:
    """
    qry = session.query(CloseDayRecord)
    qry = qry.filter(
        and_(CloseDayRecord.day >= from_day,
             CloseDayRecord.day <= to_day)
    )
    res = qry.all()

    for closeday in res:
        session.delete(closeday)
    session.commit()


def cleanup_all_db(from_dt: datetime, session):
    """
    Function to cleanup all records from all tables older than a given datetime
    :param from_dt:
    :param session: Already initialised DB-session
    :return: {'counts_deleted': x, 'mu_stat_deleted': y, 'mismatches_deleted': z}
    """
    qry_counts = session.query(PeopleCounts)
    counts_deleted = qry_counts.filter(PeopleCounts.timestamp < int(from_dt.timestamp())).delete()

    qry_mu_stat = session.query(MonitorUnitStatusRecord)
    mu_stat_deleted = qry_mu_stat.filter(MonitorUnitStatusRecord.timestamp < int(from_dt.timestamp())).delete()

    qry_mismatch = session.query(MismatchRecord)
    mismatch_deleted = qry_mismatch.filter(MismatchRecord.timestamp < int(from_dt.timestamp())).delete()

    session.commit()

    cleanup_older_closeday(from_dt.date(), session)

    return {'counts_deleted': counts_deleted, 'mu_stat_deleted': mu_stat_deleted, 'mismatches_deleted': mismatch_deleted}


def get_accuracy_mismatch_based(days_since: int, session):
    """
    Function to perform a self-estimation on accuracy, based on last `n` days mismatches
    :param days_since: last daily mismatches to be considered
    :param session: Already initialised DB-session
    :return:
    """
    ts = (datetime.now() - timedelta(days=days_since, minutes=10)).timestamp()

    qry = session.query(MismatchRecord)
    qry = qry.filter(MismatchRecord.timestamp >= ts)
    res = qry.all()

    all_inout = 0
    all_tot = 0
    inout_balance = 0
    for mm in res:
        mm: MismatchRecord
        inout = mm.entered + mm.exited
        acc_tmp = (inout) - abs(mm.estimated)
        all_inout += inout
        all_tot += abs(mm.estimated)
        inout_balance += mm.estimated

    acc_w = 0 if all_inout == 0 else (all_inout-all_tot)/all_inout

    assert acc_w <= 1, "WRONG Accuracy estimation! ( >1 ) "

    acc_perc = int(acc_w*100)

    majority_mismatch = 'Both Entr.s/Exits' if inout_balance == 0 else 'Exits' if inout_balance > 0 else 'Entrances'

    return {'accuracy_perc': acc_perc, 'tot_counts': all_inout, 'most_mismatch_on': majority_mismatch}
