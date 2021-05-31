from deemon.app import Deemon, download, monitor
from pathlib import Path
import logging
import os
import sys

logger = logging.getLogger(__name__)


class BatchJobs(Deemon):

    def export_artists(self, path):
        export_path = Path(path)
        export_file = Path(export_path / "deemon-artists.csv")
        with open(export_file, "w+") as f:
            artist_dump = self.db.get_all_artists()
            for line in artist_dump:
                line = ','.join(map(str, line))
                f.write(line + "\n")
        logger.info(f"Artists have been exported to {export_file}")

    @staticmethod
    def import_artists(path):
        import_artists = path
        # TODO check db for existing artist
        if import_artists:
            if Path(import_artists).is_file():
                with open(import_artists) as f:
                    # TODO check for CSV!
                    import_list = f.read().splitlines()
            elif Path(import_artists).is_dir():
                import_list = os.listdir(import_artists)
                num_to_import = len(import_list)
                logger.info(f"Importing {num_to_import} artist(s)...")
            else:
                logger.error("Unrecognized import type")
                sys.exit(1)

            dl = download.Download(login=False)

            for artist in import_list:
                ma = monitor.Monitor()
                ma.artist = artist
                ma.start_monitoring()

            dl.refresh(import_list)
