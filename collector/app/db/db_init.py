from db.db_closedays import CloseDayRecord
from db.db_mismatch import MismatchRecord
from db.monitorunitstatus import MonitorUnitStatusRecord
from db.people_count import PeopleCounts
from db.db_base import Base, engine

CloseDayRecord
MismatchRecord
PeopleCounts
MonitorUnitStatusRecord


def create_all_tables():
    Base.metadata.create_all(engine)
