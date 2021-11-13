import logging
import platform
import sys
import time
from pathlib import Path

import click
from packaging.version import parse as parse_version

from deemon import __version__
from deemon.cmd import download, rollback, backup, extra
from deemon.cmd.artistconfig import artist_lookup
from deemon.cmd.monitor import Monitor
from deemon.cmd.profile import ProfileConfig
from deemon.cmd.refresh import Refresh
from deemon.cmd.search import Search
from deemon.cmd.show import Show
from deemon.core import notifier
from deemon.core.config import Config, LoadProfile
from deemon.core.db import Database
from deemon.core.logger import setup_logger
from deemon.utils import startup, dataprocessor, validate

logger = None
config = None
db = None

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True,
             no_args_is_help=True)
@click.option('--whats-new', is_flag=True, help="Show release notes from this version")
@click.option('-P', '--profile', help="Specify profile to run deemon as")
@click.version_option(__version__, '-V', '--version', message='deemon %(version)s')
@click.option('-v', '--verbose', is_flag=True, help="Show debug output")
def run(whats_new, verbose, profile):
    """Monitoring and alerting tool for new music releases using the Deezer API.

    deemon is a free and open source tool. To report issues or to contribute,
    please visit https://github.com/digitalec/deemon
    """
    global logger
    global config
    global db

    setup_logger(log_level='DEBUG' if verbose else 'INFO', log_file=startup.get_log_file())
    logger = logging.getLogger(__name__)
    logger.debug(f"deemon {__version__}")
    logger.debug(f"command: \"{' '.join([x for x in sys.argv[1:]])}\"")
    logger.debug("Python " + platform.python_version())
    logger.debug(platform.platform())
    logger.debug(f"deemon appdata is located at {startup.get_appdata_dir()}")
    
    if whats_new:
        return startup.get_changelog(__version__)

    config = Config()
    db = Database()

    db.do_upgrade()
    tid = db.get_next_transaction_id()
    config.set('tid', tid, validate=False)

    if profile:
        profile_config = db.get_profile(profile)
        if profile_config:
            LoadProfile(profile_config)
        else:
            logger.error(f"Profile {profile} does not exist.")
            sys.exit(1)
    else:
        profile_config = db.get_profile_by_id(1)
        if profile_config:
            LoadProfile(profile_config)

    last_checked: int = int(db.last_update_check())

    next_check: int = last_checked + (config.check_update() * 86400)

    if config.release_channel() != db.get_release_channel()['value']:
        # If release_channel has changed, check for latest release
        logger.debug(f"Release channel changed to '{config.release_channel()}'")
        db.set_release_channel()
        last_checked = 1

    if time.time() >= next_check or last_checked == 0:
        logger.debug(f"Checking for updates ({config.release_channel()})...")
        config.set('update_available', 0, False)
        latest_ver = str(startup.get_latest_version(config.release_channel()))
        if latest_ver:
            db.set_latest_version(latest_ver)
        db.set_last_update_check()

    new_version = db.get_latest_ver()
    if parse_version(new_version) > parse_version(__version__):
        config.set('update_available', new_version, False)
        print("*" * 50)
        logger.info(f"* New version is available: v{__version__} -> v{new_version}")
        if config.release_channel() == "beta":
            logger.info("* To upgrade, run `pip install --upgrade --pre deemon`")
        else:
            logger.info("* To upgrade, run `pip install --upgrade deemon`")
        print("*" * 50)
        print("")

    config.set("start_time", int(time.time()), False)


@run.command(name='test')
def test():
    """Test email server settings by sending a test notification"""
    notification = notifier.Notify()
    notification.test()


@run.command(name='download', no_args_is_help=True)
@click.argument('artist', nargs=-1, required=False)
@click.option('-A', '--album-id', multiple=True, metavar='ID', type=int, help='Download by album ID')
@click.option('-a', '--after', 'from_date', metavar="YYYY-MM-DD", type=str, help='Grab releases released after this date')
@click.option('-B', '--before', 'to_date', metavar="YYYY-MM-DD", type=str, help='Grab releases released before this date')
@click.option('-b', '--bitrate', metavar="BITRATE", help='Set custom bitrate for this operation')
@click.option('-f', '--file', metavar='FILE', help='Download batch of artists and/or artist IDs from file')
@click.option('-i', '--artist-id', multiple=True, metavar='ID', type=int, help='Download by artist ID')
@click.option('-m', '--monitored', is_flag=True, help='Download all currently monitored artists')
@click.option('-o', '--download-path', metavar="PATH", type=str, help='Specify custom download directory')
@click.option('-t', '--record-type', metavar="TYPE", type=str, help='Specify record types to download')
@click.option('-u', '--url', metavar='URL', multiple=True, help='Download by URL of artist/album/track/playlist')
def download_command(artist, artist_id, album_id, url, file, bitrate,
                     record_type, download_path, from_date, to_date,
                     monitored):
    """
    Download specific artist, album ID or by URL

    \b
    Examples:
        download Mozart
        download -i 100 -t album -b 9
    """
    if bitrate:
        config.set('bitrate', bitrate)
    if download_path:
        config.set('download_path', download_path)
    if record_type:
        config.set('record_type', record_type)

    if monitored:
        artists, artist_ids, album_ids, urls = None, None, None, None
    else:
        artists = dataprocessor.csv_to_list(artist) if artist else None
        artist_ids = [x for x in artist_id] if artist_id else None
        album_ids = [x for x in album_id] if album_id else None
        urls = [x for x in url] if url else None

    if download_path and download_path != "":
        if Path(download_path).exists:
            config.set('download_path', download_path)
            logger.debug(f"Download path has changed: {config.download_path()}")
        else:
            return logger.error(f"Invalid download path: {download_path}")

    dl = download.Download()
    dl.set_dates(from_date, to_date)
    dl.download(artists, artist_ids, album_ids, urls, file)


@run.command(name='monitor', context_settings={"ignore_unknown_options": False}, no_args_is_help=True)
@click.argument('artist', nargs=-1)
@click.option('-a', '--alerts', is_flag=True, help="Enable or disable alerts")
@click.option('-b', '--bitrate', metavar="BITRATE", help="Specify bitrate")
@click.option('-D', '--download', 'dl', is_flag=True, help='Download all releases matching record type')
@click.option('-d', '--download-path', type=str, metavar="PATH", help='Specify custom download directory')
@click.option('-I', '--import', 'im', metavar="PATH", help="Monitor artists/IDs from file or directory")
@click.option('-i', '--artist-id', is_flag=True, help="Monitor artist by ID")
@click.option('-p', '--playlist', is_flag=True, help='Monitor Deezer playlist by URL')
@click.option('-u', '--url', is_flag=True, help='Monitor artist by URL')
@click.option('-R', '--remove', is_flag=True, help='Stop monitoring an artist')
@click.option('-s', '--search', 'search_flag', is_flag=True, help='Show similar artist results to choose from')
@click.option('-T', '--time-machine', multiple=True, type=str, metavar="YYYY-MM-DD", help="Refresh newly added artists on this date")
@click.option('-t', '--record-type', metavar="TYPE", type=str, help='Specify record types to download')
def monitor_command(artist, im, playlist, bitrate, record_type, alerts, artist_id,
                    dl, remove, url, download_path, search_flag, time_machine):
    """
    Monitor artist for new releases by ID, URL or name.

    \b
    Examples:
        monitor Mozart
        monitor --artist-id 100
        monitor --url https://www.deezer.com/us/artist/000
    """
    monitor = Monitor()
    if download_path:
        if Path(download_path).exists():
            download_path = Path(download_path)
        else:
            return logger.error("Invalid download path provided")

    if time_machine:
        time_machine_dates = [x for x in time_machine]
        time_machine = []
        for d in time_machine_dates:
            validated = validate.validate_date(d)
            if not validated:
                return logger.error("Date for time machine is invalid")
            time_machine.append(validated)
        monitor.time_machine = time_machine
    
    if not alerts:
        alerts = None

    monitor.set_options(remove, dl, search_flag)
    monitor.set_config(bitrate, alerts, record_type, download_path)

    if url:
        artist_id = True
        urls = [x.replace(",", "") for x in artist]
        artist = []
        for u in urls:
            id_from_url = u.split('/artist/')
            try:
                aid = int(id_from_url[1])
            except (IndexError, ValueError):
                logger.error(f"Invalid URL -- {url}")
                return
            artist.append(aid)

    if playlist:
        urls = [x.replace(",", "") for x in artist]
        playlist_id = []
        for u in urls:
            id_from_url = u.split('/playlist/')
            try:
                aid = int(id_from_url[1])
            except (IndexError, ValueError):
                logger.error(f"Invalid playlist URL -- {url}")
                return
            playlist_id.append(aid)

    if im:
        monitor.importer(im)
    elif playlist:
        monitor.playlists(playlist_id)
    elif artist_id:
        monitor.artist_ids(dataprocessor.csv_to_list(artist))
    elif artist:
        monitor.artists(dataprocessor.csv_to_list(artist))


@run.command(name='refresh')
@click.argument('NAME', nargs=-1, type=str, required=False)
@click.option('-p', '--playlist', is_flag=True, help="Refresh a specific playlist by name")
@click.option('-s', '--skip-download', is_flag=True, help="Skips downloading of new releases")
@click.option('-T', '--time-machine', metavar='DATE', type=str, help='Refresh as if it were this date (YYYY-MM-DD)')
def refresh_command(name, playlist, skip_download, time_machine):
    """Check artists for new releases"""

    if time_machine:
        time_machine = validate.validate_date(time_machine)
        if not time_machine:
            return logger.error("Date for time machine is invalid")

    logger.info(":: Starting database refresh")
    refresh = Refresh(time_machine, skip_download)
    if playlist:
        if not len(name):
            return logger.warning("You must provide the name of a playlist")
        refresh.run(playlists=dataprocessor.csv_to_list(name))
    elif name:
        refresh.run(artists=dataprocessor.csv_to_list(name))
    else:
        refresh.run()


@click.group(name="show")
def show_command():
    """
    Show monitored artists and latest releases
    """


@show_command.command(name="artists")
@click.argument('artist', nargs=-1, required=False)
@click.option('-c', '--csv', is_flag=True, help='Output artists as CSV')
@click.option('-e', '--export', type=Path, help='Export CSV data to file; same as -ce')
@click.option('-f', '--filter', type=str, help='Specify filter for CSV output')
@click.option('-H', '--hide-header', is_flag=True, help='Hide header on CSV output')
@click.option('-i', '--artist-id', is_flag=True, help='Show artist info by artist ID')
def show_artists(artist, artist_id, csv, export, filter, hide_header):
    """Show artist info monitored by profile"""
    if artist:
        artist = ' '.join([x for x in artist])

    show = Show()
    show.monitoring(artist=True, query=artist, export_csv=csv, save_path=export, filter=filter, hide_header=hide_header,
                    is_id=artist_id)


@show_command.command(name="playlists")
@click.argument('title', nargs=-1, required=False)
@click.option('-c', '--csv', is_flag=True, help='Output artists as CSV')
@click.option('-f', '--filter', type=str, help='Specify filter for CSV output')
@click.option('-H', '--hide-header', is_flag=True, help='Hide header on CSV output')
@click.option('-i', '--playlist-id', is_flag=True, help='Show playlist info by playlist ID')
def show_artists(title, playlist_id, csv, filter, hide_header):
    """Show playlist info monitored by profile"""
    if title:
        title = ' '.join([x for x in title])

    show = Show()
    show.monitoring(artist=False, query=title, export_csv=csv, filter=filter, hide_header=hide_header, is_id=playlist_id)


@show_command.command(name="releases")
@click.argument('N', default=7)
@click.option('-f', '--future', is_flag=True, help='Display future releases')
def show_releases(n, future):
    """
    Show list of new or future releases
    """
    show = Show()
    show.releases(n, future)


run.add_command(show_command)


@run.command(name="backup")
@click.option('-i', '--include-logs', is_flag=True, help='include log files in backup')
@click.option('-r', '--restore', is_flag=True, help='Restore from existing backup')
def backup_command(restore, include_logs):
    """Backup configuration and database to a tar file"""

    if restore:
        backup.restore()
    else:
        backup.run(include_logs)


# TODO @click.option does not support nargs=-1; unable to use spaces without quotations
@run.command(name="api", help="View raw API data for artist, artist ID or playlist ID", hidden=True)
@click.option('-A', '--album-id', type=int, help='Get album ID result via API')
@click.option('-a', '--artist', type=str, help='Get artist result via API')
@click.option('-i', '--artist-id', type=int, help='Get artist ID result via API')
@click.option('-l', '--limit', type=int, help='Set max number of artist results; default=1', default=1)
@click.option('-p', '--playlist-id', type=int, help='Get playlist ID result via API')
@click.option('-r', '--raw', is_flag=True, help='Dump as raw data returned from API')
def api_test(artist, artist_id, album_id, playlist_id, limit, raw):
    """View API result - for testing purposes"""
    import deezer
    dz = deezer.Deezer()
    if artist or artist_id:
        if artist:
            result = dz.api.search_artist(artist, limit=limit)['data']
        else:
            result = dz.api.get_artist(artist_id)

        if raw:
            if isinstance(result, list):
                for row in result:
                    for key, value in row.items():
                        print(f"{key}: {value}")
                    print("\n")
            else:
                for key, value in result.items():
                    print(f"{key}: {value}")
        else:
            if isinstance(result, list):
                for row in result:
                    print(f"Artist ID: {row['id']}\nArtist Name: {row['name']}\n")
            else:
                print(f"Artist ID: {result['id']}\nArtist Name: {result['name']}")

    if album_id:
        result = dz.api.get_album(album_id)

        if raw:
            for key, value in result.items():
                print(f"{key}: {value}")
        else:
            print(f"Album ID: {result['id']}\nAlbum Title: {result['title']}")

    if playlist_id:
        result = dz.api.get_playlist(playlist_id)

        if raw:
            for key, value in result.items():
                print(f"{key}: {value}")
        else:
            print(f"Playlist ID: {result['id']}\nPlaylist Title: {result['title']}")


@run.command(name="reset")
def reset_db():
    """Reset monitoring database"""
    logger.warning("** WARNING: All artists and playlists will be removed regardless of profile! **")
    confirm = input(":: Type 'reset' to confirm: ")
    if confirm.lower() == "reset":
        print("")
        db.reset_database()
    else:
        logger.info("Reset aborted. Database has NOT been modified.")
    return


@run.command(name='profile')
@click.argument('profile', required=False)
@click.option('-a', '--add', is_flag=True, help="Add new profile")
@click.option('-c', '--clear', is_flag=True, help="Clear config for existing profile")
@click.option('-d', '--delete', is_flag=True, help="Delete an existing profile")
@click.option('-e', '--edit', is_flag=True, help="Edit an existing profile")
def profile_command(profile, add, clear, delete, edit):
    """Add, modify and delete configuration profiles"""

    pc = ProfileConfig(profile)
    if profile:
        if add:
            pc.add()
        elif clear:
            pc.clear()
        elif delete:
            pc.delete()
        elif edit:
            pc.edit()
        else:
            pc.show()
    else:
        pc.show()

@run.command(name="extra")
def extra_command():
    """Fetch extra release info"""
    extra.main()

@run.command(name="search")
def search():
    """Interactively search and download/monitor artists"""
    client = Search()
    client.search_menu()


@run.command(name="config")
@click.argument('artist', nargs=-1, required=True)
def config_command(artist):
    """Configure per-artist settings by name or ID"""
    artist = ' '.join([x for x in artist])
    artist_lookup(artist)


@run.command(name="rollback", no_args_is_help=True)
@click.argument('num', type=int, required=False)
@click.option('-v', '--view', is_flag=True, help="View recent refresh transactions")
def rollback_command(num, view):
    """Rollback a previous monitor or refresh transaction"""
    if view:
        rollback.view_transactions()
    elif num:
        rollback.rollback_last(num)

