import logging

from deemon.core.config import Config as config
from deemon.utils import dates
from deemon.core.db import Database
import operator
import itertools

logger = logging.getLogger(__name__)
db = Database()

def view_transactions():
    tr = db.get_transactions()
    if not tr:
        return logger.info("No transactions are available to be rolled back.")

    for i, ld in enumerate(tr, start=1):
        release_id = []
        artist_names = []
        playlist_titles = []

        for k, v in ld.items():
            if (k == "releases" or k == "playlist_tracks") and ld[k]:
                for item in ld[k]:
                    for key, val in item.items():
                        if key == "album_id" or key == "track_id":
                            if item[key] not in release_id:
                                release_id.append(item[key])
            if k == "monitor" and ld[k]:
                if ld[k] not in artist_names:
                    artist_names.append(ld[k][0]['artist_name'])
            if k == "playlists" and ld[k]:
                if ld[k] not in playlist_titles:
                    playlist_titles.append(ld[k][0]['title'])

        release_id_len = len(release_id)

        if release_id_len == 1:
            release_text = f" and {release_id_len} release"
        elif release_id_len > 1:
            release_text = f" and {release_id_len} releases"
        else:
            release_text = ""

        if len(artist_names) > 1:
            if len(playlist_titles) > 1:
                playlist_text = f", {len(playlist_titles)} playlists"
            elif len(playlist_titles) == 1:
                playlist_text = f", {len(playlist_titles)} playlist"
            else:
                playlist_text = ""
            output_text = f"Added {artist_names[0]} + {len(artist_names) - 1}{playlist_text}{release_text}"
        elif len(artist_names) == 1:
            if len(playlist_titles) > 1:
                playlist_text = f", {len(playlist_titles)} playlists"
            elif len(playlist_titles) == 1:
                playlist_text = f", {len(playlist_titles)} playlist"
            else:
                playlist_text = ""
            output_text = f"Added {artist_names[0]}{playlist_text}{release_text}"
        else:
            if len(playlist_titles) > 1:
                output_text = f"Added {playlist_titles[0]} + {len(playlist_titles) - 1}{release_text}"
            elif len(playlist_titles) == 1:
                output_text = f"Added {playlist_titles[0]}{release_text}"
            else:
                output_text = f"Added {release_text[4:]}"

        print(f"{i}. {dates.get_friendly_date(ld['timestamp'])} - {output_text}")

    rollback = None
    while rollback not in range(len(tr)):
        rollback = input("\nSelect specific refresh to rollback (or Enter to exit): ")
        if rollback == "":
            return
        try:
            rollback = int(rollback) - 1
        except ValueError:
            logger.error("Invalid input")

    rollback = tr[rollback][0]['id']
    logger.debug(f"Rolling back transaction {rollback}")
    db.rollback_refresh(rollback)

def rollback_last(i: int):
    db.rollback_last_refresh(i)
    logger.info(f"Rolled back the last {i} transaction(s).")
