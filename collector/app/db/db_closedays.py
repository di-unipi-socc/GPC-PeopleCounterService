from db.db_base import Base
from sqlalchemy import Column, Integer, Date


class CloseDayRecord(Base):
    __tablename__ = 'close_days'
    id = Column(Integer, primary_key=True)
    day = Column('day', Date, unique=True)

    def __init__(self, day):
        self.day = day
