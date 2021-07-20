from deemon.app import settings, monitor, download, notify
from deemon.app.logger import setup_logger
from deemon.app.batch import BatchJobs
from deemon.app.refresh import Refresh
from deemon.app.show import ShowStats
from deemon import __version__
from datetime import datetime
from deemon.app import utils
from pathlib import Path
import tarfile
import logging
import click
import sys

logger = logging.getLogger(__name__)

appdata = utils.get_appdata_dir()
utils.init_appdata_dir(appdata)
settings = settings.Settings()
settings.load_config()
config = settings.config


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.version_option(__version__, '--version', message='deemon %(version)s')
def run(verbose):
    """Monitoring and alerting tool for new music releases using the Deezer API.

    deemon is a free and open source tool. To report issues or to contribute,
    please visit https://github.com/digitalec/deemon
    """
    setup_logger(log_level='DEBUG' if verbose else 'INFO', log_file=utils.get_log_file())

    new_version = utils.check_version()
    if new_version:
        print("*" * 50)
        logger.info(f"* New version is available: v{__version__} -> v{new_version}")
        logger.info("* To upgrade, run `pip install --upgrade deemon`")
        print("*" * 50)


@run.command(name='test')
def test():
    """Test email server settings by sending a test notification"""
    notification = notify.Notify()
    notification.test()


@run.command(name='download')
@click.option('-a', '--artist', metavar='NAME', type=str, help='Download all by artist name')
@click.option('-i', '--artist-id', metavar='ID', type=int, help='Download all by artist ID')
@click.option('-A', '--album-id', metavar='ID', type=int, help='Download by album ID')
@click.option('-u', '--url', metavar='URL', help='Download by URL of artist/album/track')
@click.option('-f', '--file', 'input_file', metavar='FILE', help='Download batch of artists from file, one per line')
@click.option('-b', '--bitrate', metavar='N', type=int, default=config["bitrate"],
              help='Set custom bitrate for this operation')
@click.option('-r', '--record-type', metavar='TYPE', default=config["record_type"],
              help='Only get certain record types')
def download_command(artist, artist_id, album_id, url, input_file, bitrate, record_type):
    """Download specific artist, album ID or by URL"""

    params = {
        'artist': artist,
        'artist_id': artist_id,
        'album_id': album_id,
        'url': url,
        'bitrate': bitrate,
        'record_type': record_type,
        'file': input_file
    }

    dl = download.Download()
    dl.download(params)


@run.command(name='monitor', context_settings={"ignore_unknown_options": True})
@click.argument('artist', nargs=-1)
@click.option('-i', '--artist-id', multiple=True, type=int, metavar="ID", help="Monitor artist by ID")
@click.option('-p', '--playlist', multiple=True, metavar="URL", help='Monitor Deezer playlist by URL', hidden=True)
@click.option('-u', '--url', multiple=True, metavar="URL", help='Monitor artist by URL')
@click.option('-s', '--skip-refresh', is_flag=True, help='Skip refresh after adding or removing artist')
@click.option('-R', '--remove', is_flag=True, help='Stop monitoring an artist')
def monitor_command(artist, playlist, artist_id, skip_refresh, remove, url):
    """
    Monitor artist for new releases by ID, URL or name.

    \b
    Examples:
        monitor Mozart
        monitor --artist-id 100
        monitor --url https://www.deezer.com/us/artist/000
    """

    artists = ' '.join(artist)
    artists = artists.split(',')
    artists = [x.lstrip() for x in artists]

    artist_id = list(artist_id)
    url = list(url)
    playlists = list(playlist)

    for a in artists:
        mon = monitor.Monitor()
        mon.artist = a

        if remove:
            mon.stop_monitoring()
        else:
            mon.start_monitoring()

    for aid in artist_id:
        mon = monitor.Monitor()
        mon.artist_id = aid

        if remove:
            mon.stop_monitoring()
        else:
            mon.start_monitoring()

    for p in playlists:
        id_from_url = p.split('/playlist/')
        try:
            playlist_id = int(id_from_url[1])
        except (IndexError, ValueError):
            logger.error(f"Invalid playlist URL -- {p}")
            sys.exit(1)

        mon = monitor.Monitor()
        mon.playlist_id = playlist_id

        # if remove:
        #     mon.stop_monitoring()
        # else:
        mon.start_monitoring_playlist()

    for u in url:
        id_from_url = u.split('/artist/')
        try:
            artist_id = int(id_from_url[1])
        except (IndexError, ValueError):
            logger.error(f"Invalid URL -- {url}")
            sys.exit(1)

        mon = monitor.Monitor()
        mon.artist_id = artist_id

        if remove:
            mon.stop_monitoring()
        else:
            mon.start_monitoring()

    if not skip_refresh:
        refresh = Refresh()
        refresh.refresh()


@run.command(name='refresh')
@click.option('-s', '--skip-download', is_flag=True, help="Skips downloading of new releases")
def refresh_command(skip_download):
    """Check artists for new releases"""
    refresh = Refresh(skip_download=skip_download)
    refresh.refresh()


@run.command(name='show')
@click.option('-a', '--artists', is_flag=True, help='Show artists currently being monitored')
@click.option('-c', '--csv', is_flag=True, help='Used with --artists, output artists as CSV')
@click.option('-n', '--new-releases', metavar='N', type=int, help='Show new releases from last N days')
@click.option('-s', '--stats', is_flag=True, help='Show various usage stats')
def show_command(artists, new_releases, stats, csv):
    """
    Show monitored artists, latest new releases and various statistics
    """
    show = ShowStats()
    if artists:
        show.artists(csv)
    elif new_releases:
        show.releases(new_releases)
    elif stats:
        show.stats()


@run.command(name='import')
@click.argument('path')
def import_cmd(path):
    """Import artists from CSV, text file or directory"""
    batch = BatchJobs()
    batch.import_artists(path)


@run.command()
@click.option('--include-logs', is_flag=True, help='include log files in backup')
def backup(include_logs):
    """Backup configuration and database to a tar file"""

    def filter_func(item):
        exclusions = ['deemon/backups']
        if not include_logs:
            exclusions.append('deemon/logs')
        if item.name not in exclusions:
            return item

    backup_tar = datetime.today().strftime('%Y%m%d-%H%M%S') + ".tar"
    backup_path = Path(settings.config_path / "backups")

    with tarfile.open(backup_path / backup_tar, "w") as tar:
        tar.add(settings.config_path, arcname='deemon', filter=filter_func)
        logger.info(f"Backed up to {backup_path / backup_tar}")

