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
        releases = 0
        artist_name = []

        for ld in e:

            for k, v in ld.items():
                if (k == "album_id" or k == "track_id") and ld[k]:
                    releases += 1
                if k == "artist_name" and ld[k]:
                    if ld[k] not in artist_name:
                        artist_name.append(ld[k])

        if releases == 1:
            release_text = f"and {releases} release"
        elif releases > 1:
            release_text = f"and {releases} releases"
        else:
            release_text = ""

        if len(artist_name) > 1:
            artist_text = f"Added {artist_name[0]} + {len(artist_name) -1} artist(s) {release_text}"
        elif len(artist_name) == 1:
            artist_text = f"Added {artist_name[0]} {release_text}"
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
