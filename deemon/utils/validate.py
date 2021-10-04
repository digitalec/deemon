import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_date(d):
    try:
        return datetime.strptime(d, '%Y-%m-%d')
    except ValueError:
        return False
