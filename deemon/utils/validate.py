import logging
from datetime import datetime
from .constants import RECORD_TYPES, BITRATES, RELEASE_CHANNELS

logger = logging.getLogger(__name__)


def validate_date(d):
    try:
        return datetime.strptime(d, '%Y-%m-%d')
    except ValueError:
        return False


def validate_record_type(record_types: list):
    """
    Check record_types and return list of invalid types
    """
    if all(elem in record_types for elem in RECORD_TYPES.values()):
        return []
    else:
        invalid_rt = [elem for elem in record_types if elem not in RECORD_TYPES.values()]
        return invalid_rt


def validate_bitrates(bitrate: str):
    """
    Check bitrate and return True if validated
    """
    br = bitrate.upper()
    if br in BITRATES.values():
        return True
    else:
        return


def validate_release_channel(channel: str):
    """
    Check release channel value and return True if validated
    """
    if channel.lower() in RELEASE_CHANNELS:
        return True
    else:
        return
