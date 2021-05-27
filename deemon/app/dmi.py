from pathlib import Path
from deemix.app import deemix
from deemon.app.settings import Settings
import logging

logger = logging.getLogger("deemon")


class DeemixInterface(deemix):
    def __init__(self, download_path, config_dir=None):
        logger.debug("Initializing deemix library")
        dm_logger = logging.getLogger("deemix")
        dm_logger.setLevel(logging.WARN)

        super().__init__(config_dir, overwriteDownloadFolder=download_path)

    def download_url(self, url, bitrate=None):
        logger.debug(url)
        for link in url:
            if ';' in link:
                for l in link.split(";"):
                    self.qm.addToQueue(self.dz, l, self.set.settings, bitrate)
            else:
                self.qm.addToQueue(self.dz, link, self.set.settings, bitrate)

    def login(self):
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
