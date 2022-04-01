from db.db_base import Base
from sqlalchemy import Column, Integer, String, Numeric


class MonitorUnitStatusRecord(Base):
    __tablename__ = 'mu_status'
    id = Column(Integer, primary_key=True)
    gate_id = Column('gate_id', String(32))
    timestamp = Column('timestamp', Numeric)
    status_code = Column('code', Integer)
    msg = Column('msg', String(32))

    def __init__(self, timestamp, gate_id, status_code, msg):
        self.timestamp = timestamp
        self.gate_id = gate_id
        self.status_code = status_code
        self.msg = msg
