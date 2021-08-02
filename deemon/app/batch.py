from deemon.app import Deemon, download, monitor
from deemon.app.refresh import Refresh
from pathlib import Path
import tqdm
import logging
import sys

logger = logging.getLogger(__name__)


class BatchJobs(Deemon):

    def import_artists(self, path, artist_ids=False):
        import_artists = path
        import_as_ids = artist_ids
        if import_artists:
            if Path(import_artists).is_file():
                with open(import_artists, encoding="utf8", errors="replace") as f:
                    import_list = sorted(f.read().splitlines())
                    num_to_import = len(import_list)
                # TODO move to function to check for CSV
                if num_to_import == 1:
                    for i in import_list[0].split(','):
                        import_list.append(i)
                    import_list.remove(import_list[0])
                    num_to_import = len(import_list)
                logger.debug(f"Detected {num_to_import} artist(s) to import")
            elif Path(import_artists).is_dir():
                import_list = [x.relative_to(import_artists) for x in sorted(Path(import_artists).iterdir()) if x.is_dir()]
                num_to_import = len(import_list)
                logger.debug(f"Detected {num_to_import} artist(s) to import")
            else:
                logger.error(f"File or directory not found: {import_artists}")
                sys.exit(1)

            progress = tqdm.tqdm(import_list, ascii=" #",
                                 bar_format='{desc}...  {n_fmt}/{total_fmt} [{bar:40}] {percentage:3.0f}%')

            import_count = 0
            import_error = 0
            for artist in progress:
                progress.set_description("Importing")
                ma = monitor.Monitor()
                if not import_as_ids:
                    ma.artist = artist
                else:
                    ma.artist_id = artist
                imported = ma.start_monitoring()
                if imported == 1:
                    import_count += 1
                elif imported == 2:
                    import_error += 1
            if import_count > 0:
                logger.info(f"** Successful: {import_count} | Errors: {import_error}")
            else:
                logger.info(f"** No new artists to import | Errors: {import_error}")
            self.db.commit()

            print()
            refresh = Refresh()
            refresh.refresh()
