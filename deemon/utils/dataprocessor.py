import logging

logger = logging.getLogger(__name__)


def read_file_as_csv(file):
    with open(file, 'r', encoding="utf8", errors="replace") as f:
        make_csv = f.read().replace('\n', ',')
        csv_to_list = make_csv.split(',')
        sorted_list = sorted(list(filter(None, csv_to_list)))
        return sorted_list


def process_input_file(artist_list):
    logger.debug("Processing file contents")
    int_artists = []
    str_artists = []
    for i in range(len(artist_list)):
        try:
            int_artists.append(int(artist_list[i]))
        except ValueError:
            str_artists.append(artist_list[i])
    logger.debug(f"Detected {len(int_artists)} artist ID(s) and {len(str_artists)} artist name(s)")
    return int_artists, str_artists


def artists_to_csv(a):
    csv_artists = ' '.join(a)
    csv_artists = csv_artists.split(',')
    csv_artists = [x.lstrip() for x in csv_artists]
    return csv_artists
