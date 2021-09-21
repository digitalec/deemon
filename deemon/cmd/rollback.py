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

    for i, e in enumerate(tr, start=1):
        release_id = []
        artist_names = []
        playlist_titles = []

        for ld in e:

            for k, v in ld.items():
                if (k == "album_id" or k == "track_id") and ld[k]:
                    if ld[k] not in release_id:
                        release_id.append(ld[k])
                if k == "artist_name" and ld[k]:
                    if ld[k] not in artist_names:
                        artist_names.append(ld[k])
                if k == "title" and ld[k]:
                    if ld[k] not in playlist_titles:
                        playlist_titles.append(ld[k])

        release_id_len = len(release_id)

        if release_id_len == 1:
            release_text = f"and {release_id_len} release"
        elif release_id_len > 1:
            release_text = f"and {release_id_len} releases"
        else:
            release_text = ""

        if len(playlist_titles) > 1:
            playlist_text = f"{playlist_titles[0]} + {len(playlist_titles) - 1} playlists(s)"
        elif len(playlist_titles) == 1:
            playlist_text = f"{playlist_titles[0]}"
        else:
            playlist_text = ""

        if len(artist_names) > 1:
            artist_text = f"Added {artist_names[0]} + {len(artist_names) - 1} artist(s) {release_text}"
        elif len(artist_names) == 1:
            artist_text = f"Added {artist_names[0]} {release_text}"
        else:
            artist_text = f"Found {release_text[4:]}"

        print(f"{i}. {dates.get_friendly_date(ld['timestamp'])} - {artist_text}")

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
