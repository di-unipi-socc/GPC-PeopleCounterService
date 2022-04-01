import configs.secrets_conf as secrets_conf

auth_server = secrets_conf.auth_server
app_secret_key = secrets_conf.app_secret_key
DEFAULT_TIMEZONE = "Europe/Rome"

ssl_cert = secrets_conf.ssl_cert
ssl_key = secrets_conf.ssl_key

USERS = secrets_conf.USERS
USERS_PASS = secrets_conf.USERS_PASS
USERS_EMAIL = secrets_conf.USERS_EMAIL
USER_DB_LOCATION = secrets_conf.USER_DB_LOCATION

SQLALCHEMY_DATABASE_URI = f'sqlite:///{USER_DB_LOCATION}'

VIDEO_ENABLE_LS = []
QRY_CNT_ENABLE_LS = []
QRY_EVT_ENABLE_LS = []
QRY_DEV_ENABLE_LS = []
RESET_ENABLE_LS = []
CLOSE_DAYS_ENABLE_LS = []
MANAGE_USERS_ENABLE_LS = []

UPDATE_ENABLE_LS = []

ALL_UNITS = secrets_conf.ALL_UNITS
ALL_STR = ''

MAIL_SERVER = ''
MAIL_PORT = 12345
MAIL_USE_TLS = True
MAIL_USE_SSL = True
email_addr = secrets_conf.email_addr
email_pass = secrets_conf.email_pass

DISABLE_ENABLE_URL = secrets_conf.DISABLE_ENABLE_URL

email_alert_recipients = []
email_anomal_activities_recipients = []

EMAIL_USER_ENABLE = set()
EMAIL_USER_ENABLE.update(email_alert_recipients, email_anomal_activities_recipients)

WS_PORT_VIDEO = 12345
WS_PORT_UPDATES = 12345
WS_PORT_MSG = 12345

WS_PING_TIMEOUT = 100
WS_PING_INTERVAL = 100
WS_CLOSE_TIMEOUT = 100

DB_ADDR_DEFAULT = secrets_conf.DB_ADDR_DEFAULT
DB_USR = secrets_conf.DB_USR
DB_PASS = secrets_conf.DB_PASS
DB_PORT = secrets_conf.DB_PORT
DB_NAME = secrets_conf.DB_NAME

DB_CLEAN_DAYS_BEFORE = 1
DB_NEXT_CLEAN_DAYS = 1

RESET_RECORD_NAME = ''

NOW_TIMERANGE = (0, 0)
assert 0 <= NOW_TIMERANGE[0] < 24
assert 0 <= NOW_TIMERANGE[1] < 24

NIGHT_TIMERANGE = (0, 0)
assert 0 <= NIGHT_TIMERANGE[0] < 24
assert 0 <= NIGHT_TIMERANGE[1] < NIGHT_TIMERANGE[0]

CLOSE_DAYS_DISPLAY_RANGE = (365, 365)

H_DAILY_REPORT = 0
H_NIGHT_REPORT = 0

WEEK_CLOSE_DAYS = []  # 0='mon' --- 6='sun'
INST_ALERT_REFRESH_RATE = 1
INST_ALERT_RENEW_RANGE_H = 1
INST_ALERT_TRIGGER_P_NUM = 1

MU_IS_ALIVE_T = 10

ACCURACY_DAYS = 90

video_token = secrets_conf.video_token
