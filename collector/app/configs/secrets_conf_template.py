import os

auth_server = (os.getenv(''), os.getenv(''))
app_secret_key = os.getenv('')

email_addr = os.getenv('')
email_pass = os.getenv('')
DISABLE_ENABLE_URL = os.getenv('')

ssl_cert = os.getenv('')
ssl_key = os.getenv('')

USERS = [os.getenv(''),
         os.getenv(''),
         os.getenv(''),
         os.getenv('')
         ]
USERS_EMAIL = [os.getenv(''),
               os.getenv(''),
               os.getenv(''),
               os.getenv('')
               ]
USERS_PASS = [
    os.getenv(''),
    os.getenv(''),
    os.getenv(''),
    os.getenv('')
]

USER_DB_LOCATION = os.getenv('')

DB_ADDR_DEFAULT = os.getenv('')
DB_USR = os.getenv('')
DB_PASS = os.getenv('')
DB_PORT = int(os.getenv(''))
DB_NAME = os.getenv('')

ALL_UNITS = {os.getenv(''),
             os.getenv(''),
             os.getenv(''),
             os.getenv('')
             }

video_token = os.getenv('')
