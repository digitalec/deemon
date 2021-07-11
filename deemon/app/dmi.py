from pathlib import Path
from deezer import Deezer
from deemix import generateDownloadObject
from deemix.downloader import Downloader
from deemix.settings import load as loadSettings
import deemix.utils.localpaths as localpaths
import logging

logger = logging.getLogger(__name__)


class DeemixInterface():
    def __init__(self, download_path, config_dir=None):
        super().__init__()
        logger.debug("Initializing deemix library")
        self.dz = Deezer()
        self.config_dir = localpaths.getConfigFolder()

    def download_url(self, url, bitrate):
        settings = loadSettings(self.config_dir)
        links = []
        for link in url:
            if ';' in link:
                for l in link.split(";"):
                    links.append(l)
            else:
                links.append(link)
        for link in links:
            download_object = generateDownloadObject(self.dz, link, bitrate)
            if isinstance(download_object, list):
                for obj in download_object:
                    Downloader(self.dz, obj, settings).start()
            else:
                Downloader(self.dz, download_object, settings).start()

    def login(self):
        logger.info("Verifying ARL is valid, please wait...")
        if Path(self.config_dir).is_dir():
            if Path(self.config_dir / '.arl').is_file():
                with open(self.config_dir / '.arl', 'r') as f:
                    arl = f.readline().rstrip("\n")
                    logger.debug(f"ARL found: {arl}")
                if not self.dz.login_via_arl(arl):
                    logger.error(f"ARL is expired or invalid")
                    return False
            else:
                logger.error(f"ARL not found in {self.config_dir}")
                return False
        else:
            logger.error(f"ARL directory {self.config_dir} was not found")
            return False
        return True
