from deemon.app import settings, monitor, download
from deemon.app.show import ShowStats
from deemon.app.batch import BatchJobs
from deemon.app.logger import setup_logger
from deemon import __version__
from datetime import datetime
from deemon.app import utils
from pathlib import Path
import tarfile
import logging
import click

logger = logging.getLogger(__name__)

appdata = utils.get_appdata_dir()
utils.init_appdata_dir(appdata)
settings = settings.Settings()
settings.load_config()
config = settings.config


@click.group()
@click.option('-t', '--test-alerts', is_flag=True, help='Test your SMTP settings')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.version_option(__version__, '-V', '--version', message='deemon %(version)s')
def run(verbose, test_alerts):
    """Monitoring and alerting tool for new music releases using the Deezer API.

    deemon is a free and open source tool. To report issues or to contribute,
    please visit https://github.com/digitalec/deemon
    """
    setup_logger(log_level='DEBUG' if verbose else 'INFO', log_file=utils.get_log_file())


@run.command(name='download')
@click.option('-a', '--artist', metavar='NAME', help='Download all by artist name')
@click.option('-i', '--artist-id', metavar='ID', type=int, help='Download all by artist ID')
@click.option('-A', '--album-id', metavar='ID', type=int, help='Download by album ID')
@click.option('-u', '--url', metavar='URL', help='Download by URL of artist/album/track')
@click.option('-b', '--bitrate', metavar='N', type=int, default=config["bitrate"],
              help='Set custom bitrate for this operation')
@click.option('-r', '--record-type', metavar='TYPE', default=config["record_type"],
              help='Only get certain record types')
def download_command(artist, artist_id, album_id, url, bitrate, record_type):
    """Download specific artist, album ID or by URL"""
    params = {
        'artist': artist,
        'artist_id': artist_id,
        'album_id': album_id,
        'url': url,
        'bitrate': bitrate,
        'record_type': record_type
    }
    dl = download.Download()
    dl.download(params)


@run.command(name='monitor', context_settings={"ignore_unknown_options": True})
@click.argument('artist', nargs=-1)
@click.option('-R', '--remove', is_flag=True, help='Stop montioring an artist')
@click.option('-u', '--url', metavar='URL', help='Monitor by URL of artist/album/track')
def monitor_command(artist, remove, url):
    """Monitor ARTIST for new releases"""

    artist_id = None
    artist_csv = None

    if url:
        split_url = url.split('/artist/')
        artist_id = int(split_url[1])

        ma = monitor.Monitor()
        ma.artist_id = artist_id
        ma.start_monitoring()

    else:
        artist_csv = ' '.join(artist).split(',')
        artist_csv = [x.lstrip() for x in artist_csv]

        for artist in artist_csv:
            ma = monitor.Monitor()
            ma.artist = artist

            if remove:
                ma.stop_monitoring()
            else:
                ma.start_monitoring()

    dl = download.Download(login=False)
    dl.refresh(artist_id if artist_id else artist_csv)


@run.command()
def refresh():
    """Check artists for new releases"""
    dl = download.Download()
    dl.refresh()


@run.command(name='show')
@click.option('-a', '--artists', is_flag=True, help='Show artists currently being monitored')
@click.option('-n', '--new-releases', metavar='N', type=int, help='Show new releases from last N days')
@click.option('-s', '--stats', is_flag=True, help='Show various usage stats')
def show_command(artists, new_releases, stats):
    """
    Show monitored artists, latest new releases and various statistics
    """
    show = ShowStats()
    if artists:
        show.artists()
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
@click.argument('path')
def export(path):
    """Export all artists"""
    batch = BatchJobs()
    batch.export_artists(path)


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

