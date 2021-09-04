import deezer

from deemon.utils.menu import Menu
from deemon.core.config import Config
from deemon.cmd.download import Download, QueueItem


def search(name: str, limit: int = 10):
    dz = deezer.Deezer()
    queue_list = []
    config = Config()
    api_result = dz.api.search_artist(name, limit=limit)['data']

    if len(api_result) > 0:
        m = Menu(f"Search results for \"{name}\": ", api_result)
        artist = m.gen_artist_menu()[0]
        if artist:
            artist_id = artist['id']
            artist_albums = dz.api.get_artist_albums(artist_id)['data']
            m = Menu(f"Discography for \"{artist['name']}\": ", artist_albums, artist_id)
            to_download = m.get_album_menu()
            if isinstance(to_download, list) and len(to_download) > 0:
                for album in to_download:
                    queue_list.append(
                        QueueItem(
                            download_path=config.download_path(),
                            bitrate=config.bitrate(),
                            artist=artist,
                            album=album)
                    )
                dl = Download()
                dl.queue_list = queue_list
                dl.download_queue()
