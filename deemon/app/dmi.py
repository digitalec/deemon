from pathlib import Path
from logging import getLogger, WARN
from deemix.app import deemix


class DeemixInterface(deemix):
    def __init__(self, download_path, config_dir=None):
        dm_logger = getLogger('deemix')
        dm_logger.setLevel(WARN)
        super().__init__(config_dir, overwriteDownloadFolder=download_path)

    def download_url(self, url, bitrate=None):
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
