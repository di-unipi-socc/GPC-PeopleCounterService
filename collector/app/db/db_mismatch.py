from db.db_base import Base
from sqlalchemy import Column, Integer, Numeric


class MismatchRecord(Base):
    __tablename__ = 'mismatches'
    id = Column(Integer, primary_key=True)
    timestamp = Column('timestamp', Numeric)
    entered = Column('entered', Integer)
    exited = Column('exited', Integer)
    estimated = Column('estimated', Integer)

    def __init__(self, timestamp, entered, exited, estimated):
        self.timestamp = timestamp
        self.entered = entered
        self.exited = exited
        self.estimated = estimated
