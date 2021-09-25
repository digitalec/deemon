from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def validate_date(d):
    try:
        datetime.strptime(d, '%Y-%m-%d')
    except ValueError:
        return False
    return True
