
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from configs.config import DB_ADDR_DEFAULT, DB_USR, DB_PASS, DB_PORT, DB_NAME

DB_ADDR = os.getenv('DB_SERVER_ADDR')
if DB_ADDR is None:
    DB_ADDR = DB_ADDR_DEFAULT
print(DB_ADDR)

_DB_USR = DB_USR
_DB_PASS = DB_PASS
_DB_PORT = DB_PORT
_DB_NAME = DB_NAME

engine = create_engine(f'postgresql://{_DB_USR}:{_DB_PASS}@{DB_ADDR}:{_DB_PORT}/{_DB_NAME}', pool_pre_ping=True)

Session = sessionmaker(bind=engine)

Base = declarative_base()
