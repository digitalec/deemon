from deemon.app import settings, monitor, download, notify, utils
from deemon.app.logger import setup_logger
from deemon.app.refresh import Refresh
from deemon.app.show import ShowStats
from deemon import __version__
from datetime import datetime
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

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.version_option(__version__, '-V', '--version', message='deemon %(version)s')
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
@click.argument('artist', nargs=-1)
@click.option('-i', '--artist-id', multiple=True, metavar='ID', type=int, help='Download by artist ID')
@click.option('-A', '--album-id', multiple=True, metavar='ID', type=int, help='Download by album ID')
@click.option('-u', '--url', metavar='URL', multiple=True, help='Download by URL of artist/album/track/playlist')
@click.option('-f', '--file', metavar='FILE', help='Download batch of artists and/or artist IDs from file')
@click.option('-b', '--bitrate', default=config["bitrate"], help='Set custom bitrate for this operation')
@click.option('-t', '--record-type', type=click.Choice(['all', 'album', 'ep', 'single'], case_sensitive=False),
              default=config["record_type"], help='Specify record types to download')
def download_command(artist, artist_id, album_id, url, file, bitrate, record_type):
    """
    Download specific artist, album ID or by URL

    \b
    Examples:
        download Mozart
        download -i 100 -t album -b 9
    """
    bitrate = utils.validate_bitrate(bitrate)

    artists = artists_to_csv(artist) if artist else None
    artist_ids = [x for x in artist_id] if artist_id else None
    album_ids = [x for x in album_id] if album_id else None
    urls = [x for x in url] if url else None

    dl = download.Download()
    dl.download(artists, artist_ids, album_ids, urls, bitrate, record_type, file)


@run.command(name='monitor', context_settings={"ignore_unknown_options": True})
@click.argument('artist', nargs=-1)
@click.option('-i', '--artist-id', multiple=True, type=int, metavar="ID", help="Monitor artist by ID")
@click.option('-I', '--import', 'im', metavar="PATH", help="Monitor artists/IDs from file or directory")
@click.option('-u', '--url', multiple=True, metavar="URL", help='Monitor artist by URL')
@click.option('-p', '--playlist', multiple=True, metavar="URL", help='Monitor Deezer playlist by URL')
@click.option('-b', '--bitrate', default=config["bitrate"], help="Specify bitrate")
@click.option('-t', '--record-type', type=click.Choice(['all', 'album', 'ep', 'single'], case_sensitive=False),
              default=config["record_type"], help='Specify record types to download')
@click.option('-a', '--alerts', type=int, default=config["alerts"], help="Enable or disable alerts")
@click.option('-n', '--no-refresh', is_flag=True, help='Skip refresh after adding or removing artist')
@click.option('-D', '--download', 'dl', is_flag=True, help='Download all releases matching record type')
@click.option('-R', '--remove', is_flag=True, help='Stop monitoring an artist')
@click.option('--reset', is_flag=True, help='Remove all artists/playlists from monitoring')
def monitor_command(artist, im, playlist, no_refresh, bitrate, record_type, alerts, artist_id, remove, url, reset, dl):
    """
    Monitor artist for new releases by ID, URL or name.

    \b
    Examples:
        monitor Mozart
        monitor --artist-id 100
        monitor --url https://www.deezer.com/us/artist/000
    """
    if reset:
        logger.warning("** ALL ARTISTS AND PLAYLISTS WILL BE REMOVED! **")
        confirm = input("Type 'reset' to confirm: ")
        if confirm == "reset":
            monitor.monitor(None, None, None, None, None, reset=True)
        else:
            logger.info("Reset aborted. Database has NOT been modified.")
        return

    artist_id = list(artist_id)
    url = list(url)
    playlists = list(playlist)

    new_artists = []
    new_playlists = []

    alerts = utils.validate_alerts(alerts)
    bitrate = utils.validate_bitrate(bitrate)

    if dl:
        dl = download.Download()

    if im:
        if Path(im).is_file():
            imported_file = utils.read_file_as_csv(im)
            artist_int_list, artist_str_list = utils.process_input_file(imported_file)
            if artist_str_list:
                for a in artist_str_list:
                    result = monitor.monitor("artist", a, bitrate, record_type, alerts, remove=remove, dl_obj=dl)
                    if type(result) == int:
                        new_artists.append(result)
            if artist_int_list:
                for aid in artist_int_list:
                    result = monitor.monitor("artist_id", aid, bitrate, record_type, alerts, remove=remove, dl_obj=dl)
                    if type(result) == int:
                        new_artists.append(result)
        elif Path(im).is_dir():
            import_list = [x.relative_to(im) for x in sorted(Path(im).iterdir()) if x.is_dir()]
            for a in import_list:
                result = monitor.monitor("artist", a, bitrate, record_type, alerts, remove=remove, dl_obj=dl)
                if type(result) == int:
                    new_artists.append(result)
        else:
            logger.error(f"File or directory not found: {im}")
            return

    if artist:
        for a in artists_to_csv(artist):
            result = monitor.monitor("artist", a, bitrate, record_type, alerts, remove=remove, dl_obj=dl)
            if type(result) == int:
                new_artists.append(result)

    if url:
        for u in url:
            id_from_url = u.split('/artist/')
            try:
                aid = int(id_from_url[1])
            except (IndexError, ValueError):
                logger.error(f"Invalid URL -- {url}")
                sys.exit(1)
            artist_id.append(aid)

    if artist_id:
        for aid in artist_id:
            result = monitor.monitor("artist_id", aid, bitrate, record_type, alerts, remove=remove, dl_obj=dl)
            if type(result) == int:
                new_artists.append(result)

    if playlists:
        for p in playlists:
            result = monitor.monitor("playlist", p, bitrate, record_type, alerts, remove=remove, dl_obj=dl)
            if type(result) == int:  # TODO is this needed? What return values are possible? if result > 0?
                new_playlists.append(result)

    if (len(new_artists) > 0 or len(new_playlists) > 0) and not no_refresh:
        logger.debug("Requesting refresh, standby...")
        logger.debug(f"new_artists={new_artists}")
        logger.debug(f"new_playlists={new_playlists}")
        Refresh(artist_id=new_artists, playlist_id=new_playlists, dl_obj=dl)


@run.command(name='refresh')
@click.option('-s', '--skip-download', is_flag=True, help="Skips downloading of new releases")
@click.option('-t', '--time-machine', metavar='DATE', type=str, help='Refresh as if it were this date (YYYY-MM-DD)')
def refresh_command(skip_download, time_machine):
    """Check artists for new releases"""
    Refresh(skip_download=skip_download, time_machine=time_machine)


@run.command(name='show')
@click.option('-a', '--artists', is_flag=True, help='Show artists currently being monitored')
@click.option('-i', '--artist-ids', is_flag=True, help='Show artist IDs currently being monitored')
@click.option('-p', '--playlists', is_flag=True, help='Show playlists currently being monitored', hidden=True)
@click.option('-c', '--csv', is_flag=True, help='Used with -a, -i, -p; output artists as CSV')
@click.option('-n', '--new-releases', metavar='N', type=int, help='Show new releases from last N days')
def show_command(artists, artist_ids, playlists, new_releases, csv):
    """
    Show monitored artists, latest new releases and various statistics
    """
    show = ShowStats()
    if artists or artist_ids:
        show.artists(csv, artist_ids)
    elif playlists:
        show.playlists(csv)
    elif new_releases:
        show.releases(new_releases)


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


def artists_to_csv(a):
    csv_artists = ' '.join(a)
    csv_artists = csv_artists.split(',')
    csv_artists = [x.lstrip() for x in csv_artists]
    return csv_artists