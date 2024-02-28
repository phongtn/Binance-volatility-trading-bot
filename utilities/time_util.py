from datetime import datetime
import pytz

DEFAULT_TIME_ZONE = 'Asia/Saigon'


def convert_timestamp(timestamp):
    dt_object = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    dt_object = dt_object.astimezone(pytz.timezone(DEFAULT_TIME_ZONE))
    return dt_object.isoformat()


def now():
    return datetime.now(pytz.timezone(DEFAULT_TIME_ZONE)).isoformat()


def now_str():
    return str(datetime.now(pytz.timezone(DEFAULT_TIME_ZONE)).replace(microsecond=0))
