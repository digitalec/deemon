import logging
from csv import reader

logger = logging.getLogger(__name__)


def read_file_as_csv(file):
    with open(file, 'r', encoding="utf-8-sig", errors="replace") as f:
        make_csv = f.read()
        csv_to_list = make_csv.split('\n')
        sorted_list = sorted(list(filter(None, csv_to_list)))
        return sorted_list


def process_input_file(artist_list):
    logger.debug("Processing file contents")
    try:
        artists = [int(x) for x in artist_list]
        logger.debug(f"File detected as containing {len(artists)} artist IDs")
    except ValueError:
        artists = [x for x in artist_list]
        logger.debug(f"File detected as containing {len(artists)} artist names")
    return artists


def csv_to_list(all_artists) -> list:
    """
    Separate artists and replace delimiter to find artists containing commas in their name
    """
    all_artists = [x for x in all_artists]
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
