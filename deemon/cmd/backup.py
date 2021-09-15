import logging
from pathlib import Path
from deemon.utils import startup
import tarfile
from datetime import datetime


logger = logging.getLogger(__name__)


def run(include_logs: bool = False):

    def filter_func(item):
        exclusions = ['deemon/backups']
        if not include_logs:
            exclusions.append('deemon/logs')
        if item.name not in exclusions:
            return item

    backup_tar = datetime.today().strftime('%Y%m%d-%H%M%S') + ".tar"
    backup_path = Path(startup.get_appdata_dir() / "backups")

    with tarfile.open(backup_path / backup_tar, "w") as tar:
        tar.add(startup.get_appdata_dir(), arcname='deemon', filter=filter_func)
        logger.info(f"Backed up to {backup_path / backup_tar}")