import logging
import time
from datetime import datetime, date

logger = logging.getLogger(__name__)


def get_todays_date():
    now_ts = int(time.time())
    today_date = datetime.utcfromtimestamp(now_ts).strftime('%Y-%m-%d')
    return today_date


def generate_date_filename(prefix: str):
    return prefix + datetime.today().strftime('%Y%m%d-%H%M%S')


def get_max_release_date(days):
    day_in_secs = 86400
    input_days_in_secs = days * day_in_secs
    max_date_ts = int(time.time()) - input_days_in_secs
    max_date = datetime.utcfromtimestamp(max_date_ts).strftime('%Y-%m-%d')
    return max_date


def get_year(release_date: str):
    return datetime.strptime(release_date, '%Y-%m-%d').year


def str_to_datetime(d: str):
    date_string = datetime.strptime(d, "%Y-%m-%d")
    return datetime.strftime(date_string, "%Y-%m-%d")


def str_to_datetime_obj(d: str):
    return datetime.strptime(d, "%Y-%m-%d")


def get_friendly_date(d: int):
    input_date = datetime.fromtimestamp(d).date()
    input_time = datetime.fromtimestamp(d).time()
    today = date.today()
    delta = today - input_date
    if delta.days == 0:
        try:
            return f"{input_time.strftime('%-I:%M %p')}"
        except ValueError:
            # Gotta keep Windows happy...
            return f"{input_time.strftime('%#I:%M %p')}"
    elif delta.days == 1:
        try:
            return f"Yesterday, {input_time.strftime('%-I:%M %p')}"
        except ValueError:
            # Gotta keep Windows happy...
            return f"Yesterday, {input_time.strftime('%#I:%M %p')}"

    elif 1 < delta.days < 7:
        try:
            return input_date.strftime("%A, ") + input_time.strftime("%-I:%M %p")
        except ValueError:
            # Gotta keep Windows happy...
            return input_date.strftime("%A, ") + input_time.strftime("%#I:%M %p")
    else:
        try:
            return input_date.strftime("%Y-%m-%d - ") + input_time.strftime("%-I:%M %p")
        except ValueError:
            # Gotta keep Windows happy...
            return input_date.strftime("%Y-%m-%d - ") + input_time.strftime("%#I:%M %p")
