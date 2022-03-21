import inspect
import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from deemon import VERSION

import tqdm

LOG_FORMATS = {
    'DEBUG': '%(asctime)s %(levelname)s %(name)s:  %(message)s',
    'INFO': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
}

STREAM_LOG_FORMATS = {
    'DEBUG': '%(message)s',
    'INFO': '%(message)s',
}

LOG_DATE = '%Y-%m-%d %H:%M:%S'


class TqdmStream(object):

    @classmethod
    def write(cls, msg):
        tqdm.tqdm.write(msg, end='')


def setup_logger(log_level='DEBUG', log_file=None):
    """
    Configure logging for the deemon application
    """

    def log_exceptions(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        print(f"[!] deemon {VERSION} has unexpectedly quit [!]")
        print("")
        print(f"     Error: {exc_type.__name__}")
        print(f"     Message: {exc_value}")
        print("")

        if exc_traceback:
            formatted_traceback = traceback.format_tb(exc_traceback)
            if len(formatted_traceback) > 4:
                print_traceback = formatted_traceback[-4:]
            else:
                print_traceback = formatted_traceback
            print("     Traceback (showing last 4 entries):")
            for lines in print_traceback:
                for line in lines.split('\n'):
                    if line != "":
                        print(f"        {line}")
            print("")
            print("Please see logs for more information.")
            logger.critical("=" * 60)
            logger.critical(f"      Uncaught Exception : {exc_type.__name__}      ")
            logger.critical("=" * 60)
            for line in formatted_traceback:
                for l in line.split('\n'):
                    if l != "":
                        logger.critical(l)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    deemon_logger = logging.getLogger("deemon")
    deemon_logger.setLevel(logging.DEBUG)

    # TODO REMOVE
    # deemix_logger = logging.getLogger("deemix")
    # deemix_logger.setLevel(logging.DEBUG)

    urllib3_logger = logging.getLogger("urllib3")
    urllib3_logger.setLevel(logging.ERROR)

    # spotipy_logger = logging.getLogger("spotipy")
    # spotipy_logger.setLevel(logging.INFO)

    del logger.handlers[:]
    # del deemix_logger.handlers[:]

    if log_file is not None:
        rotate = RotatingFileHandler(log_file, maxBytes=1048576, backupCount=1, encoding="utf-8")
        rotate.setLevel(logging.DEBUG)
        rotate.setFormatter(logging.Formatter(LOG_FORMATS['DEBUG'], datefmt=LOG_DATE))
        logger.addHandler(rotate)

    stream = logging.StreamHandler(stream=TqdmStream)
    stream.setLevel(log_level)
    stream.setFormatter(logging.Formatter(STREAM_LOG_FORMATS[log_level], datefmt=LOG_DATE))
    deemon_logger.addHandler(stream)

    sys.excepthook = log_exceptions

    logger.debug("\n")
