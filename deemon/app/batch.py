from deemon.app import Deemon, download, monitor
from deemon.app.refresh import Refresh
from pathlib import Path
import progressbar
import logging
import os
import sys

logger = logging.getLogger(__name__)


class BatchJobs(Deemon):

    def import_artists(self, path):
        import_artists = path
        # TODO check db for existing artist
        if import_artists:
            if Path(import_artists).is_file():
                with open(import_artists) as f:
                    # TODO check for CSV!
                    import_list = f.read().splitlines()
                    # TODO clean this up and merge with lines 36:37
                    num_to_import = len(import_list)
                    logger.info(f"Importing {num_to_import} artist(s), please wait...")
            elif Path(import_artists).is_dir():
                import_list = os.listdir(import_artists)
                num_to_import = len(import_list)
                logger.info(f"Importing {num_to_import} artist(s), please wait...")
            else:
                logger.error("Unrecognized import type")
                sys.exit(1)

            bar = progressbar.ProgressBar(maxval=num_to_import,
                                          widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
            bar.start()
            artists_added = []
            for idx, artist in enumerate(import_list):
                ma = monitor.Monitor()
                ma.artist = artist
                ma.start_monitoring(silent=True)
                artists_added.append(ma.artist_id)
                bar.update(idx)
            bar.finish()
            self.db.commit()

            print()
            refresh = Refresh()
            refresh.refresh()
