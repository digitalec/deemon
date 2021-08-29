from datetime import datetime
import logging
import sys

logger = logging.getLogger(__name__)

ALLOWED_BITRATES = [1, 3, 9]
ALLOWED_ALERTS = [0, 1]


def validate_bitrate(bitrate):
    logger.debug(f"Bitrate requested: {bitrate}")
    if isinstance(bitrate, str):
        if "128" in bitrate:
            bitrate = 1
        elif "320" in bitrate:
            bitrate = 3
        elif "flac" in bitrate.lower():
            bitrate = 9
        else:
            try:
                bitrate = int(bitrate)
            except ValueError:
                logger.error(f"Unknown bitrate option: {bitrate} ({str(type(bitrate).__name__)})")
                sys.exit(1)

    if bitrate == 128:
        bitrate = 1
    if bitrate == 320:
        bitrate = 3

    if bitrate not in ALLOWED_BITRATES:
        logger.error(f"Unknown bitrate option: {bitrate}")
        sys.exit(1)

    logger.debug(f"Bitrate is set to: {bitrate}")
    return bitrate


def validate_alerts(alerts):
    if alerts not in ALLOWED_ALERTS:
        logger.error(f"Invalid alert value of: {alerts}")
        sys.exit(1)
    return alerts


def validate_date(d):
    try:
        datetime.strptime(d, '%Y-%m-%d')
    except ValueError:
        return False
    return True
