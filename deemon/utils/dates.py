from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)


def get_todays_date():
    now_ts = int(time.time())
    today_date = datetime.utcfromtimestamp(now_ts).strftime('%Y-%m-%d')
    return today_date


def get_max_release_date(days):
    day_in_secs = 86400
    input_days_in_secs = days * day_in_secs
    max_date_ts = int(time.time()) - input_days_in_secs
    max_date = datetime.utcfromtimestamp(max_date_ts).strftime('%Y-%m-%d')
    return max_date

def get_year(release_date: str):
    return datetime.strptime(release_date, '%Y-%m-%d').year