import os
import time

from flask import Flask

from db.db_base import Session
from db.monitorunitstatus import MonitorUnitStatusRecord
from net_io.mail_management import MailManager
from net_io.messages_websoc import MSGManagerThreadBody, TAG_SYSADMIN
from utils.frames_dict import FramesDict

from configs.config import MU_IS_ALIVE_T

DEBUG = bool(os.getenv('DEBUG'))
IS_ALIVE_T = MU_IS_ALIVE_T
IS_STREAM_ON_T = IS_ALIVE_T


class MonitorUnitStatus:
    """
    Class that represent the Monitor unit, and offer methods to know his current status
    """
    def __init__(self, unit_name):
        self.name = unit_name
        self.t_update = time.time()
        self.seen()

    def is_alive(self):
        """
        :return: Ture if the last message received from it is no older then 20sec
        """
        # print(f'{self.name}.is_alive(self)')
        t_now = time.time()
        diff = t_now - self.t_update
        if diff > IS_ALIVE_T:
            # print(f'LAST UPDATE for: {diff} (was {self.t_update}) => NOT ALIVE')
            return False
        return True

    def seen(self):
        """
        Update the timestamp of last message received from it
        :return:
        """
        self.t_update = time.time()
        # print(f'{self.name}.seen @{self.t_update}')


class StatusManagerThreadBody:
    """
    Keep track of Monitor Units status and their outputs (count-updates and video streams).
    Exploit also the functionalities of Mail and Message Managers to communicate critical events (as monitor unit
    connection/disconnection)
    """
    def __init__(self, flsk_app: Flask,
                 frames_dict: FramesDict, mail_manager: MailManager, msg_manager: MSGManagerThreadBody):
        self.connected_units = dict()
        self.all_mu_names: set = flsk_app.config['ALL_UNITS']

        self.frames_d = frames_dict
        self.process = True
        self.app = flsk_app
        self.mail_man = mail_manager
        self.msg_man = msg_manager

        # Base.metadata.create_all(engine)

    def __call__(self):
        """
        Coroutine that keep track of
        :return:
        """
        while self.process:
            try:
                time.sleep(IS_ALIVE_T)
                self.cleanup_mu_scan()
                self.cleanup_streamers()
            except Exception as e:
                with self.app.app_context():
                    self.app.logger.error(f'StatusManager FAIL: {str(e)}')

    def someone_miss(self):
        connected_names = self.get_online_devices()
        for mu_name in self.all_mu_names:
            if mu_name not in connected_names:
                return True
        return False

    def get_online_devices(self):
        r_ls =[]
        for mu in self.connected_units.values():
            mu: MonitorUnitStatus
            r_ls.append(mu.name)
        return r_ls

    def mu_seen(self, device_id):
        if device_id not in self.connected_units:
            mu = MonitorUnitStatus(device_id)
            self.connected_units[device_id] = mu
            self.notify_new_mu(device_id)
            assert device_id in self.connected_units
        else:
            mu: MonitorUnitStatus = self.connected_units[device_id]
            mu.seen()

    def log_db_record(self, dev_id: str, code: int, msg: str):
        if not DEBUG:
            session = Session()
            log_record = MonitorUnitStatusRecord(time.time(), dev_id, code, msg)
            session.add(log_record)
            session.commit()
            session.close()

    def notify_new_mu(self, dev_id):
        self.log_db_record(dev_id, 9, 'Connected')
        msg = f'Monitoring Unit {dev_id} JOIN'
        with self.app.app_context():
            self.app.logger.info(msg)
        self.msg_man.send_message_to(TAG_SYSADMIN, 'MU JOIN', msg, 'info', 15)
        self.mail_man.broadcast_alert_email('Monitor Unit: CONNECT', msg)

    def notify_rm_mu(self, dev_id):
        # print(f'notify_rm(self, {dev_id})')
        self.log_db_record(dev_id, -9, 'Device Connection Lost')
        msg = f'Monitoring Unit {dev_id} LOST'
        with self.app.app_context():
            self.app.logger.error(msg)
        self.msg_man.send_message_to(TAG_SYSADMIN, 'MU DISCONNECT', msg, 'danger', 20)
        self.mail_man.broadcast_alert_email('Monitor Unit: LOST', msg)

    def remove_mu(self, device_id):
        # print(f'remove_mu(self, {device_id})')
        assert device_id in self.connected_units
        if device_id not in self.connected_units:
            return
        rm_mu = self.connected_units.pop(device_id)
        assert not(device_id in self.connected_units)
        # del rm_mu
        self.notify_rm_mu(device_id)

    def cleanup_mu_scan(self):
        rm_ls = []
        mu_names = list(self.connected_units.keys())
        for mu_name in mu_names:
            mu: MonitorUnitStatus = self.connected_units[mu_name]
            if not mu.is_alive():
                assert mu_name in self.connected_units
                self.remove_mu(mu_name)

    def cleanup_streamers(self):
        t_now = time.time()
        for dev_id in self.frames_d.get_streamers():
            if t_now - self.frames_d.last_update(dev_id) > IS_STREAM_ON_T:
                msg = f'[{dev_id}] Video LOST since {int(t_now - self.frames_d.last_update(dev_id))}s'
                self.frames_d.remove_streamer(dev_id)
                with self.app.app_context():
                    self.app.logger.error(msg)
                self.msg_man.send_message_to(TAG_SYSADMIN, 'Video LOST', msg, 'danger', 30)
                self.log_db_record(dev_id, -4, 'Video-Stream Lost')
