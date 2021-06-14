from deemix.app import deemix
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DeemixInterface(deemix):
    def __init__(self, download_path, config_dir=None):
        logger.debug("Initializing deemix library")
        super().__init__(config_dir, overwriteDownloadFolder=download_path)

    def download_url(self, urls: list, bitrate: int):
        for url in urls:
            if ';' in url:
                for link in url.split(";"):
                    self.qm.addToQueue(self.dz, link, self.set.settings, bitrate)
            else:
                self.qm.addToQueue(self.dz, url, self.set.settings, bitrate)

    def login(self):
        logger.info("Verifying ARL is valid, please wait...")
        config_dir = Path(self.set.configFolder)
        if Path(config_dir).is_dir():
            if Path(config_dir / '.arl').is_file():
                with open(config_dir / '.arl', 'r') as f:
                    arl = f.readline().rstrip("\n")
                    logger.debug(f"ARL found: {arl}")
                if not self.dz.login_via_arl(arl):
                    logger.error(f"ARL is expired or invalid")
                    return False
            else:
                logger.error(f"ARL not found in {config_dir}")
                return False
        else:
            logger.error(f"ARL directory {config_dir} was not found")
            return False
        return True


