import logging
from csv import reader

logger = logging.getLogger(__name__)


def read_file_as_csv(file, split_new_line=True):
    with open(file, 'r', encoding="utf-8-sig", errors="replace") as f:
        make_csv = f.read()
        if split_new_line:
            csv_to_list = make_csv.split('\n')
        else:
            csv_to_list = make_csv.split(', ')
        sorted_list = sorted(list(filter(None, csv_to_list)))
        sorted_list = list(set(sorted_list))
        return sorted_list


def process_input_file(artist_list):
    logger.debug("Processing file contents")
    try:
        artists = [int(x) for x in artist_list]
        total_artist_count = len(artists)
        logger.debug(f"File detected as containing {total_artist_count} artist IDs")
        logger.debug("Checking for duplicates")
        artists_removed_duplicates = list(set(artists))
        new_artists_count = len(artists_removed_duplicates)
        duplicates = total_artist_count - new_artists_count
        if duplicates:
            logger.debug(f"Removed {duplicates} duplicate(s)")
        else:
            logger.debug("No duplicates found, continuing...")

    except ValueError:
        artists = [x for x in artist_list]
        total_artist_count = len(artists)
        logger.debug(f"File detected as containing {len(artists)} artist names")

        artists_removed_duplicates = list(set(artists))
        new_artists_count = len(artists_removed_duplicates)
        duplicates = total_artist_count - new_artists_count
        if duplicates:
            logger.debug(f"Removed {duplicates} duplicate(s)")

    logger.info(f"Detected {new_artists_count} unique artists")
    return artists_removed_duplicates


def csv_to_list(all_artists) -> list:
    """
    Separate artists and replace delimiter to find artists containing commas in their name
    """
    all_artists = [str(x) for x in all_artists]
    processed_artists = []
    for artist in all_artists:
        if artist[-1] == ',':
            processed_artists.append(artist[:-1] + "|")
        else:
            processed_artists.append(artist)
    processed_artists = ' '.join(processed_artists)
    processed_artists = processed_artists.split('|')

    result = []
    csv_artists = reader(processed_artists, delimiter="|")
    for line in csv_artists:
        combined_line = ([x.lstrip() for x in line])
        result.append(','.join(combined_line))
    return (result)
