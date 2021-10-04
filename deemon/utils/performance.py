import logging
import time

logger = logging.getLogger(__name__)


def timeit(method):
    def timed(*args, **kwargs):
        ts = time.time()
        result = method(*args, **kwargs)
        te = time.time()

        logger.debug(f"{method.__name__} finished in ({str((te - ts))})")
        return result

    return timed
