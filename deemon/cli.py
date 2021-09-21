import platform
import logging
import sys
from deemon.core.logger import setup_logger
from deemon.utils import startup, dataprocessor
from deemon.core import notifier
from deemon import __version__
from packaging.version import parse as parse_version
from deemon.cmd import monitor, download, rollback
from deemon.core.db import Database
from deemon.core.config import Config, LoadProfile
from deemon.cmd.profile import ProfileConfig
from deemon.cmd.search import Search
from deemon.cmd.refresh import Refresh
from deemon.cmd.show import Show
from deemon.cmd.artistconfig import artist_lookup
from deemon.cmd import backup
from pathlib import Path
import click

logger = None
config = None
db = None

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-P', '--profile', help="Specify profile to run deemon as")
@click.version_option(__version__, '-V', '--version', message='deemon %(version)s')
@click.option('-v', '--verbose', is_flag=True, help="Show debug output")
def run(verbose, profile):
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

    check_interval: int = config.check_update() - 3600

    if config.release_channel() != db.get_release_channel()['value']:
        # If release_channel has changed, check for latest release
        logger.info(f"Release channel changed to '{config.release_channel()}', checking for updates...")
        db.set_release_channel()
        last_checked = 0

    if last_checked < check_interval or last_checked == 0:
        config.set('update_available', 0, False)
        latest_ver = startup.get_latest_version(config.release_channel())
        if latest_ver:
            db.set_latest_version(latest_ver)
        db.set_last_update_check()

    new_version = db.get_latest_ver()
    if parse_version(new_version) > parse_version(__version__):
        config.set('update_available', 1, False)
        print("*" * 50)
        logger.info(f"* New version is available: v{__version__} -> v{new_version}")
        if config.release_channel() == "beta":
            logger.info("* To upgrade, run `pip install --upgrade --pre deemon`")
        else:
            logger.info("* To upgrade, run `pip install --upgrade deemon`")
        print("*" * 50)
        print("")


@run.command(name='test')
def test():
    """Test email server settings by sending a test notification"""
    notification = notifier.Notify()
    notification.test()


@run.command(name='download')
@click.argument('artist', nargs=-1)
@click.option('-A', '--album-id', multiple=True, metavar='ID', type=int, help='Download by album ID')
@click.option('-b', '--bitrate', metavar="BITRATE", help='Set custom bitrate for this operation')
@click.option('-F', '--from-date', metavar="YYYY-MM-DD", type=str, help='Grab releases from this date forward')
@click.option('-f', '--file', metavar='FILE', help='Download batch of artists and/or artist IDs from file')
@click.option('-i', '--artist-id', multiple=True, metavar='ID', type=int, help='Download by artist ID')
@click.option('-o', '--download-path', metavar="PATH", type=str, help='Specify custom download directory')
@click.option('-t', '--record-type', metavar="TYPE", type=str, help='Specify record types to download')
@click.option('-u', '--url', metavar='URL', multiple=True, help='Download by URL of artist/album/track/playlist')
def download_command(artist, artist_id, album_id, url, file, bitrate, record_type, download_path, from_date):
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

    artists = dataprocessor.artists_to_csv(artist) if artist else None
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
    dl.download(artists, artist_ids, album_ids, urls, file, from_date=from_date)


@run.command(name='monitor', context_settings={"ignore_unknown_options": False})
@click.argument('artist', nargs=-1)
@click.option('-a', '--alerts', metavar="BOOL", type=str, help="Enable or disable alerts")
@click.option('-b', '--bitrate', metavar="BITRATE", help="Specify bitrate")
@click.option('-D', '--download', 'dl', is_flag=True, help='Download all releases matching record type')
@click.option('-d', '--download-path', type=str, metavar="PATH", help='Specify custom download directory')
@click.option('-I', '--import', 'im', metavar="PATH", help="Monitor artists/IDs from file or directory")
@click.option('-i', '--artist-id', multiple=True, type=int, metavar="ID", help="Monitor artist by ID")
@click.option('-n', '--no-refresh', is_flag=True, help='Skip refresh after adding or removing artist')
@click.option('-p', '--playlist', multiple=True, metavar="URL", help='Monitor Deezer playlist by URL')
@click.option('-u', '--url', multiple=True, metavar="URL", help='Monitor artist by URL')
@click.option('-R', '--remove', is_flag=True, help='Stop monitoring an artist')
@click.option('-s', '--search', 'search_flag', is_flag=True, help='Show similar artist results to choose from')
@click.option('-t', '--record-type', metavar="TYPE", type=str, help='Specify record types to download')
def monitor_command(artist, im, playlist, no_refresh, bitrate, record_type, alerts, artist_id, remove,
                    url, dl, download_path, search_flag):
    """
    Monitor artist for new releases by ID, URL or name.

    \b
    Examples:
        monitor Mozart
        monitor --artist-id 100
        monitor --url https://www.deezer.com/us/artist/000
    """
    if not config.transaction_id():
        tid = db.new_transaction()
        config.set('tid', tid, validate=False)

    artist_id = list(artist_id)
    url = list(url)
    playlists = list(playlist)

    new_artists = []
    new_playlists = []
    cfg = {}

    if bitrate:
        cfg['bitrate'] = bitrate
    if download_path:
        cfg['download_path'] = download_path
    if record_type:
        cfg['record_type'] = record_type
    if alerts:
        cfg['alerts'] = alerts

    if download_path and download_path != "":
        if Path(download_path).exists:
            config.set('download_path', download_path)
            logger.debug(f"Download path has changed: {config.download_path()}")
        else:
            return logger.error(f"Invalid download path: {download_path}")

    if dl:
        dl = download.Download()

    # TODO moved import to subcommand, add option to skip line 1 for CSV header (--header)
    if im:
        if Path(im).is_file():
            imported_file = dataprocessor.read_file_as_csv(im)
            artist_int_list, artist_str_list = dataprocessor.process_input_file(imported_file)
            if artist_str_list:
                for a in artist_str_list:
                    result = monitor.monitor("artist", a, artist_config=cfg, remove=remove, dl_obj=dl, is_search=search_flag)
                    if type(result) == int:
                        new_artists.append(result)
            if artist_int_list:
                for aid in artist_int_list:
                    result = monitor.monitor("artist_id", aid, artist_config=cfg, remove=remove, dl_obj=dl, is_search=search_flag)
                    if type(result) == int:
                        new_artists.append(result)
        elif Path(im).is_dir():
            import_list = [x.relative_to(im) for x in sorted(Path(im).iterdir()) if x.is_dir()]
            for a in import_list:
                result = monitor.monitor("artist", a, artist_config=cfg, remove=remove, dl_obj=dl, is_search=search_flag)
                if type(result) == int:
                    new_artists.append(result)
        else:
            logger.error(f"File or directory not found: {im}")
            return

    if artist:
        for a in dataprocessor.artists_to_csv(artist):
            result = monitor.monitor("artist", a, artist_config=cfg, remove=remove, dl_obj=dl, is_search=search_flag)
            if isinstance(result, int):
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
            result = monitor.monitor("artist_id", aid, artist_config=cfg, remove=remove, dl_obj=dl, is_search=search_flag)
            if isinstance(result, int):
                new_artists.append(result)

    if playlists:
        for p in playlists:
            result = monitor.monitor("playlist", p, artist_config=cfg, remove=remove, dl_obj=dl, is_search=search_flag)
            if isinstance(result, int):
                new_playlists.append(result)

    if (len(new_artists) > 0 or len(new_playlists) > 0) and not no_refresh:
        logger.debug("Requesting refresh, standby...")
        Refresh(artist_id=new_artists, playlist_id=new_playlists, dl_obj=dl)


@run.command(name='refresh')
@click.argument('NAME', nargs=-1, type=str, required=False)
@click.option('-d', '--dry-run', is_flag=True, help='Simulate refresh without making any changes')
@click.option('-p', '--playlist', is_flag=True, help="Refresh a specific playlist by name")
@click.option('-r', '--rollback', metavar='N', type=int, help='Rollback last N refreshes')
@click.option('-s', '--skip-download', is_flag=True, help="Skips downloading of new releases")
@click.option('-t', '--time-machine', metavar='DATE', type=str, help='Refresh as if it were this date (YYYY-MM-DD)')
def refresh_command(name, playlist, skip_download, time_machine, rollback, dry_run):
    """Check artists for new releases"""
    if not config.transaction_id():
        tid = db.new_transaction()
        config.set('tid', tid, validate=False)

    list_of_names = []
    if name:
        name = list(name)

        for n in dataprocessor.artists_to_csv(name):
            list_of_names.append(n)
        name = list_of_names

    if name and playlist:
        playlist = list_of_names
        name = None

    Refresh(artist_name=name, playlist_title=playlist, skip_download=skip_download,
            time_machine=time_machine, rollback=rollback, dry_run=dry_run)


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
    show.monitoring(artist=True, query=artist, csv=csv, save_path=export, filter=filter, hide_header=hide_header, is_id=artist_id)


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
    show.monitoring(artist=False, query=title, csv=csv, filter=filter, hide_header=hide_header, is_id=playlist_id)


@show_command.command(name="releases")
@click.argument('N', default=7)
def show_releases(n):
    """
    Show list of new releases
    """
    show = Show()
    show.releases(n)
    # TODO add ability to download from this list

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
    logger.warning("** ALL ARTISTS AND PLAYLISTS WILL BE REMOVED! **")
    confirm = input(":: Type 'reset' to confirm: ")
    if confirm.lower() == "reset":
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


@run.command(name="search")
def search():
    """Interactively search and download/monitor artists"""
    client = Search()
    client.search_menu()


@run.command(name="config")
@click.argument('artist', nargs=-1)
def config_command(artist):
    """Configure per-artist settings by name or ID"""
    artist = ' '.join([x for x in artist])
    artist_lookup(artist)

@run.command(name="rollback")
@click.argument('num', type=int, required=False)
@click.option('-v', '--view', is_flag=True, help="View recent refresh transactions")
def rollback_command(num, view):
    if view:
        rollback.view_transactions()
    elif num:
        rollback.rollback_last(num)