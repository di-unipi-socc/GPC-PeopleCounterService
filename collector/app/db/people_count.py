from db.db_base import Base
from sqlalchemy import Column, Integer, String, Numeric


# {unique_ID, gate_id, timestamp, in#, out#, diff}
class PeopleCounts(Base):
    __tablename__ = 'people_counts'
    id = Column(Integer, primary_key=True)
    gate_id = Column('gate_id', String(32))
    timestamp = Column('timestamp', Numeric)
    entered = Column('in', Integer)
    exited = Column('out', Integer)

    def __init__(self, timestamp, gate_id, person_in, person_out):
        self.timestamp = timestamp
        self.gate_id = gate_id
        self.entered = person_in
        self.exited = person_out
