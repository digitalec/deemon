from deemon.app import Deemon
from pathlib import Path
import logging

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
