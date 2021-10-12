import logging
import os
import tarfile
from datetime import datetime
from pathlib import Path

from packaging.version import parse as parse_version
from tqdm import tqdm

from deemon import __version__
from deemon.utils import startup, dates

logger = logging.getLogger(__name__)


def run(include_logs: bool = False):
    def filter_func(item):
        includes = ['deemon', 'deemon/config.json', 'deemon/deemon.db']
        if include_logs:
            if 'deemon/logs' in item.name:
                includes.append(item.name)
        if item.name in includes:
            return item

    backup_tar = dates.generate_date_filename("backup-" + __version__ + "-") + ".tar"
    backup_path = startup.get_backup_dir()

    with tarfile.open(backup_path / backup_tar, "w") as tar:
        tar.add(startup.get_appdata_dir(), arcname='deemon', filter=filter_func)
        logger.info(f"Backed up to {backup_path / backup_tar}")


def restore():
    restore_file_list = ['deemon/config.json', 'deemon/deemon.db']

    def inspect_tar(fn: Path) -> dict:
        fn_name = fn.name
        fn_name = fn_name.replace('.tar', '').split('-')
        if fn_name[0] == "backup" and len(fn_name) > 3:
            if check_tar_contents(fn):
                backup_appversion = '-'.join(fn_name[1:-2])
                if is_newer_backup(backup_appversion):
                    logger.debug(f"Backup found for newer version {backup_appversion} is not compatible!")
                    return
                backup_time = datetime.strptime(fn_name[-1], "%H%M%S")
                backup_date = datetime.strptime(fn_name[-2], "%Y%m%d")
                try:
                    friendly_time = datetime.strftime(backup_time, "%-I:%M:%S %p")
                except ValueError:
                    # Gotta keep Windows happy...
                    friendly_time = datetime.strftime(backup_time, "%#I:%M:%S %p")
                try:
                    friendly_date = datetime.strftime(backup_date, "%b %-d, %Y")
                except ValueError:
                    # Gotta keep Windows happy...
                    friendly_date = datetime.strftime(backup_date, "%b %#d, %Y")
                backup_info = {
                    'version': backup_appversion,
                    'date': friendly_date,
                    'time': friendly_time,
                    'age': fn_name[-2] + fn_name[-1],
                    'filename': fn
                }
                return backup_info
        else:
            return

    def check_tar_contents(archive: Path):
        tar = tarfile.open(archive)
        file_list = tar.getmembers()
        files = [x.name for x in file_list]
        if all(item in files for item in restore_file_list):
            return True
        logger.debug("Archive is invalid or corrupt: " + str(archive))

    def restore_tarfile(archive: dict):
        logger.debug("Restoring backup from `" + str(archive['filename'].name + "`"))
        extract_dir = startup.get_appdata_dir()
        tar = tarfile.open(archive['filename'])
        progress = tqdm(tar.getmembers(), ascii=" #",
                        bar_format='{desc}  [{bar}] {percentage:3.0f}%')
        for member in progress:
            if member.isreg():
                if member.name in restore_file_list:
                    member.name = os.path.basename(member.name)
                    logger.info(f"Restoring {member.name}...")
                    progress.set_description_str(f"Restoring {member.name}")
                    tar.extract(member, extract_dir)
                    logger.debug(f"Restored {member.name} to {extract_dir}")
            if member == tar.getmembers()[-1]:
                progress.set_description_str("Restore complete")

    def is_newer_backup(version: str):
        if parse_version(version) > parse_version(__version__):
            return True

    def display_backup_list(available_backups: list):
        print("deemon Backup Manager\n")
        for index, backup in enumerate(available_backups, start=1):
            print(f"{index}. {backup['date']} @ {backup['time']} (ver {backup['version']})")

        selected_backup = int
        while selected_backup not in range(len(available_backups)):
            selected_backup = input("\nSelect a backup to restore (or press Enter to exit): ")
            if selected_backup == "":
                return
            try:
                selected_backup = int(selected_backup)
                selected_backup -= 1
            except ValueError:
                logger.warning("Invalid entry. Enter a number corresponding to the backup you wish to restore.")
        print("")
        restore_tarfile(available_backups[selected_backup])

    backups = []
    backup_path = startup.get_backup_dir()
    file_list = [x for x in sorted(Path(backup_path).glob('*.tar'))]
    for backup in file_list:
        tar_files = inspect_tar(backup)
        if tar_files:
            backups.append(tar_files)
    if backups:
        backups = sorted(backups, key=lambda x: x['age'], reverse=True)
        display_backup_list(backups)
    else:
        logger.info("No backups available to restore")
