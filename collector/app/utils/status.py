from datetime import datetime

from utils.status_manager import StatusManagerThreadBody
from endpoints.reset_form_utils import ResetForm
from endpoints.queries_utils import estimate_people_now
from net_io.updates_websoc import UpdateManagerThreadBody
from db.db_base import Session
from net_io.mucounts import MUCounts
from db.people_count import PeopleCounts

from configs.config import RESET_RECORD_NAME, ALL_STR

_RESET_RECORD_NAME = RESET_RECORD_NAME
ALL = ALL_STR


class GlobalStatus:
    """
    Status of Collector services.
    Interact with DB to update Counts Estimation and send Updates to the GUI clients
    """
    def __init__(self, update_manager: UpdateManagerThreadBody, status_manager: StatusManagerThreadBody):
        self.upd_mngr = update_manager
        self.stat_mngr = status_manager

    def update_count(self, update: MUCounts):
        """
        Add new records into Cunts Estimation Table, and send updated counts to the clients
        :param update:
        :return:
        """
        device = update.device_id
        self.stat_mngr.mu_seen(device)
        evts = {}
        for e in update.entrances:
            time_s = e[1]
            if not time_s in evts:
                evts[time_s] = []
            evts[time_s].append(('in', e[0]))
        for e in update.exits:
            time_s = e[1]
            if not time_s in evts:
                evts[time_s] = []
            evts[time_s].append(('out', e[0]))

        session = Session()
        for t, ls in zip(evts.keys(), evts.values()):
            entered, exits, = 0, 0
            for e in ls:
                if e[0] == 'in':
                    entered = entered + e[1]
                else:
                    exits = exits + e[1]

            count = PeopleCounts(int(t), device, entered, exits)
            session.add(count)

        session.commit()
        session.close()
        self.broadcast_counts()

    def broadcast_counts(self):
        """
        Send current Estimation People Counts to GUI client
        :return:
        """
        self.upd_mngr.some_error = self.stat_mngr.someone_miss()
        session = Session()
        counts = estimate_people_now(ALL, session)
        self.upd_mngr.broadcast_update(counts)
        session.close()

    def reset_counters(self, form: ResetForm):
        """
        Add a new fake record, to adjust current People Count.
        If a complete reset is required, get current daily Counts, and add a new record to reset it to 0.
        :param form:
        :return:
        """
        session = Session()
        try:
            _full = form.full.data
            if _full:
                current_counts = estimate_people_now(ALL, session)  # {'tot': p_cnt, 'in': p_in, 'out': p_out}
                entered = (current_counts['in']) * (-1)
                exited = (current_counts['out']) * (-1)
                rec_time = datetime.now()
            else:
                entered = form.entered.data
                exited = form.exited.data
                rec_time = form.time.data

            if entered == 0 and exited == 0:
                raise Exception(f'Nothing to Reset: Fix_Entered = {entered}, Fix_Exited = {exited}')

            return self._reset_counters(session, rec_time, entered, exited)
        finally:
            session.close()

    def _reset_counters(self, session, rec_time: datetime, entered: int, exited: int):
        """
        Add the reset record to DB
        :param session: Already initialized session
        :param rec_time: DateTime to use as record's timestamp
        :param entered:
        :param exited:
        :return:
        """
        fix_record = PeopleCounts(int(rec_time.timestamp()), _RESET_RECORD_NAME, entered, exited)
        session.add(fix_record)
        session.commit()
        self.broadcast_counts()
