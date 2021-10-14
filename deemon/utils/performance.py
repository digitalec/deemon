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


def operation_time(start_time):
    end_time = int(time.time())
    duration = end_time - start_time
    output = time.strftime("%H:%M:%S", time.gmtime(duration))
    logger.info(f"Operation completed in {output}")