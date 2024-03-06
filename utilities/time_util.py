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


def convert_seconds(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = int((total_seconds % 3600) % 60)
    return hours, minutes, seconds
