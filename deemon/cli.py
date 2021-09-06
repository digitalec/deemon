from deemon.cmd import monitor, download
from deemon.core.logger import setup_logger
from deemon.utils import notifier, startup, validate, dataprocessor
from deemon.core.db import Database
from deemon.core.config import Config
from deemon.core.settings import UserConfig, AppConfig, LoadUser
from deemon.cmd.search import search
from deemon.cmd.refresh import Refresh
from deemon.cmd.show import ShowStats
from deemon import __version__
from datetime import datetime
from pathlib import Path
import tarfile
import logging
import click
import sys

appdata = startup.get_appdata_dir()
startup.init_appdata_dir(appdata)
config = Config()
setup_logger(log_level='DEBUG' if config.debug_mode() else 'INFO', log_file=startup.get_log_file())
logger = logging.getLogger(__name__)

db = Database()

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, '-V', '--version', message='deemon %(version)s')
@click.option('-U', '--user', help="Specify user to run deemon as")
def run(user):
    """Monitoring and alerting tool for new music releases using the Deezer API.

    deemon is a free and open source tool. To report issues or to contribute,
    please visit https://github.com/digitalec/deemon
    """
    db.do_upgrade()
    if user:
        user_settings = db.get_user(user)
        if user_settings:
            LoadUser(user_settings)
        else:
            logger.error(f"User {user} does not exist.")
            sys.exit(1)
    # import deemon.core.db as database
    # db = database.DBHelper(settings.db_path)
    # last_checked = db.last_update_check()
    # check_interval = (config["check_update"] * 86400)
    # if last_checked < check_interval:
    #     new_version = startup.check_version()
    #     if new_version:
    #         print("*" * 50)
    #         logger.info(f"* New version is available: v{__version__} -> v{new_version}")
    #         logger.info("* To upgrade, run `pip install --upgrade deemon`")
    #         print("*" * 50)
    #     db.set_last_update()


@run.command(name='test')
def test():
    """Test email server settings by sending a test notification"""
    notification = notifier.Notify()
    notification.test()


@run.command(name='download')
@click.argument('artist', nargs=-1)
@click.option('-i', '--artist-id', multiple=True, metavar='ID', type=int, help='Download by artist ID')
@click.option('-A', '--album-id', multiple=True, metavar='ID', type=int, help='Download by album ID')
@click.option('-u', '--url', metavar='URL', multiple=True, help='Download by URL of artist/album/track/playlist')
@click.option('-f', '--file', metavar='FILE', help='Download batch of artists and/or artist IDs from file')
@click.option('-s', '--search', 'search_cmd', is_flag=True, help='Interactively search for and download')
@click.option('-b', '--bitrate', default=config.bitrate(), help='Set custom bitrate for this operation')
@click.option('-o', '--download-path', type=str, metavar="PATH", help='Specify custom download directory')
@click.option('-t', '--record-type', type=click.Choice(['all', 'album', 'ep', 'single'], case_sensitive=False),
              default=config.record_type(), help='Specify record types to download')
def download_command(artist, artist_id, album_id, url, file, search_cmd, bitrate, record_type, download_path):
    """
    Download specific artist, album ID or by URL

    \b
    Examples:
        download Mozart
        download -i 100 -t album -b 9
    """
    bitrate = validate.validate_bitrate(bitrate)
    if bitrate:
        config.set('bitrate', bitrate)

    if search_cmd:
        if artist:
            search_artist = ' '.join(artist)
            search(search_artist)
        else:
            logger.error("Artist name must be specified")
        return

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
    dl.download(artists, artist_ids, album_ids, urls, bitrate, record_type, file)


# TODO implement subcommands; add --include-featured-artists, --track-id options
@run.command(name='monitor', context_settings={"ignore_unknown_options": True})
@click.argument('artist', nargs=-1)
@click.option('-i', '--artist-id', multiple=True, type=int, metavar="ID", help="Monitor artist by ID")
@click.option('-I', '--import', 'im', metavar="PATH", help="Monitor artists/IDs from file or directory")
@click.option('-u', '--url', multiple=True, metavar="URL", help='Monitor artist by URL')
@click.option('-p', '--playlist', multiple=True, metavar="URL", help='Monitor Deezer playlist by URL')
@click.option('-s', '--search', 'search_flag', is_flag=True, help='Show similar artist results to choose from')
@click.option('-b', '--bitrate', default=config.bitrate(), help="Specify bitrate")
@click.option('-t', '--record-type', type=click.Choice(['all', 'album', 'ep', 'single'], case_sensitive=False),
              default=config.record_type(), help='Specify record types to download')
@click.option('-a', '--alerts', type=int, default=config.alerts(), help="Enable or disable alerts")
@click.option('-n', '--no-refresh', is_flag=True, help='Skip refresh after adding or removing artist')
@click.option('-D', '--download', 'dl', is_flag=True, help='Download all releases matching record type')
@click.option('-o', '--download-path', type=str, metavar="PATH", help='Specify custom download directory')
@click.option('-R', '--remove', is_flag=True, help='Stop monitoring an artist')
def monitor_command(artist, im, playlist, no_refresh, bitrate, record_type, alerts,
                    artist_id, remove, url, dl, download_path, search_flag):
    """
    Monitor artist for new releases by ID, URL or name.

    \b
    Examples:
        monitor Mozart
        monitor --artist-id 100
        monitor --url https://www.deezer.com/us/artist/000
    """

    artist_id = list(artist_id)
    url = list(url)
    playlists = list(playlist)

    new_artists = []
    new_playlists = []

    alerts = validate.validate_alerts(alerts)
    bitrate = validate.validate_bitrate(bitrate)

    if download_path and download_path != "":
        if Path(download_path).exists:
            config.set('download_path', download_path)
            logger.debug(f"Download path has changed: {config.download_path()}")
        else:
            return logger.error(f"Invalid download path: {download_path}")

    if dl:
        dl = download.Download()

    if im:
        if Path(im).is_file():
            imported_file = dataprocessor.read_file_as_csv(im)
            artist_int_list, artist_str_list = dataprocessor.process_input_file(imported_file)
            if artist_str_list:
                for a in artist_str_list:
                    result = monitor.monitor("artist", a, bitrate, record_type, alerts, remove=remove, dl_obj=dl,
                                             search=search_flag)
                    if type(result) == int:
                        new_artists.append(result)
            if artist_int_list:
                for aid in artist_int_list:
                    result = monitor.monitor("artist_id", aid, bitrate, record_type, alerts, remove=remove, dl_obj=dl,
                                             search=search_flag)
                    if type(result) == int:
                        new_artists.append(result)
        elif Path(im).is_dir():
            import_list = [x.relative_to(im) for x in sorted(Path(im).iterdir()) if x.is_dir()]
            for a in import_list:
                result = monitor.monitor("artist", a, bitrate, record_type, alerts, remove=remove, dl_obj=dl,
                                         search=search_flag)
                if type(result) == int:
                    new_artists.append(result)
        else:
            logger.error(f"File or directory not found: {im}")
            return

    if artist:
        for a in dataprocessor.artists_to_csv(artist):
            result = monitor.monitor("artist", a, bitrate, record_type, alerts, remove=remove, dl_obj=dl,
                                     search=search_flag)
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
            result = monitor.monitor("artist_id", aid, bitrate, record_type, alerts, remove=remove, dl_obj=dl,
                                     search=search_flag)
            if isinstance(result, int):
                new_artists.append(result)

    if playlists:
        for p in playlists:
            result = monitor.monitor("playlist", p, bitrate, record_type, alerts, remove=remove, dl_obj=dl,
                                     search=search_flag)
            if isinstance(result, int):
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


@click.group(name="show")
@click.option('-a', '--artists', is_flag=True, help='Show artists currently being monitored')
@click.option('-i', '--artist-ids', is_flag=True, help='Show artist IDs currently being monitored')
@click.option('-p', '--playlists', is_flag=True, help='Show playlists currently being monitored', hidden=True)
@click.option('-c', '--csv', is_flag=True, help='Used with -a, -i; output artists as CSV')
@click.option('-e', '--extended', is_flag=True, help='Show extended artist data')
def show_command(artists, artist_ids, playlists, csv, extended):
    """
    Show monitored artists and latest releases
    """

@show_command.command(name="artists")
@click.option('-c', '--csv', is_flag=True, help='Used with -a, -i; output artists as CSV')
@click.option('-e', '--extended', is_flag=True, help='Show extended artist data')
def show_artists(csv, extended):
    show = ShowStats()
    show.artists(csv=csv, artist_ids=False, extended=extended)

@show_command.command(name="ids")
@click.option('-c', '--csv', is_flag=True, help='Used with -a, -i; output artists as CSV')
@click.option('-e', '--extended', is_flag=True, help='Show extended artist data')
def show_ids(csv, extended):
    show = ShowStats()
    show.artists(csv=csv, artist_ids=True, extended=extended)

@show_command.command(name="playlists")
@click.option('-c', '--csv', is_flag=True, help='Used with -a, -i; output artists as CSV')
def show_playlists(csv, extended):
    show = ShowStats()
    show.playlists(csv)


@show_command.command(name="releases")
@click.argument('N', default=7)
def show_releases(n):
    """
    Show list of new releases
    """
    show = ShowStats()
    show.releases(n)


run.add_command(show_command)


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
    backup_path = Path(startup.get_config() / "backups")

    with tarfile.open(backup_path / backup_tar, "w") as tar:
        tar.add(startup.get_config(), arcname='deemon', filter=filter_func)
        logger.info(f"Backed up to {backup_path / backup_tar}")


# TODO @click.option does not support nargs=-1; unable to use spaces without quotations
@run.command(name="api", help="View raw API data for artist, artist ID or playlist ID")
@click.option('--artist', type=str, help='Get artist result via API')
@click.option('--artist-id', type=int, help='Get artist ID result via API')
@click.option('--album-id', type=int, help='Get album ID result via API')
@click.option('--playlist-id', type=int, help='Get playlist ID result via API')
@click.option('--limit', type=int, help='Set max number of artist results; default=1', default=1)
@click.option('--raw', is_flag=True, help='Dump as raw data returned from API')
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
    logger.warning("** ALL ARTISTS AND PLAYLISTS WILL BE REMOVED! **")
    confirm = input("Type 'reset' to confirm: ")
    if confirm.lower() == "reset":
        db.reset_database()
    else:
        logger.info("Reset aborted. Database has NOT been modified.")
    return



@click.group(name='config', help='Modify deemon configuration and users')
def config_command():
    pass


@click.group(name="users")
def config_users():
    """Add, modify and delete users"""

@config_users.command(name='add')
@click.argument('user')
def add(user):
    """Add a new user"""
    uc = UserConfig(user)
    uc.add()

@config_users.command(name='edit')
@click.argument('user')
def edit(user):
    """Modify existing users"""
    uc = UserConfig(user)
    uc.edit()

@config_users.command(name='show')
@click.argument('user', required=False)
def show(user=None):
    """Show settings for user(s)"""
    uc = UserConfig(user)
    uc.show()

@config_users.command(name="delete")
@click.argument('user')
def delete(user):
    """Delete an existing user"""
    uc = UserConfig(user)
    uc.delete()


config_command.add_command(config_users)
run.add_command(config_command)