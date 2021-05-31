from deemon.app import settings, dmi, db, notify
from deemix.app import deemix
from pathlib import Path
import logging
import deezer
import sys

logger = logging.getLogger(__name__)
deemix_logger = logging.getLogger("deemix")
deemix_logger.setLevel(logging.WARN)


class DeemixInterface(deemix):
    def __init__(self, download_path, config_dir=None):
        logger.debug("Initializing deemix library")
        self.deemix_logger = logging.getLogger("deemix")
        self.deemix_logger.setLevel(logging.WARN)
        super().__init__(config_dir, overwriteDownloadFolder=download_path)

    def download_url(self, urls: list, bitrate: int):
        for url in urls:
            if ';' in url:
                for link in url.split(";"):
                    self.qm.addToQueue(self.dz, link, self.set.settings, bitrate)
            else:
                self.qm.addToQueue(self.dz, url, self.set.settings, bitrate)

    def login(self):
        logger.info("Verifying ARL, please wait...")
        config_dir = Path(self.set.configFolder)
        if Path(config_dir).is_dir():
            if Path(config_dir / '.arl').is_file():
                with open(config_dir / '.arl', 'r') as f:
                    arl = f.readline().rstrip("\n")
                if not self.dz.login_via_arl(arl):
                    return False
            else:
                return False
        else:
            return False
        return True


