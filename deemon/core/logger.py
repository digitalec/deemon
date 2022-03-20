import logging
from logging.handlers import RotatingFileHandler

import tqdm

LOG_FORMATS = {
    'DEBUG': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
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

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    deemon_logger = logging.getLogger("deemon")
    deemon_logger.setLevel(logging.DEBUG)

    # TODO REMOVE
    # deemix_logger = logging.getLogger("deemix")
    # deemix_logger.setLevel(logging.DEBUG)
    #
    # urllib3_logger = logging.getLogger("urllib3")
    # urllib3_logger.setLevel(logging.ERROR)
    #
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