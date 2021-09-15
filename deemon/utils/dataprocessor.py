import csv
import logging
from csv import reader
import re

logger = logging.getLogger(__name__)


def read_file_as_csv(file):
    with open(file, 'r', encoding="utf-8", errors="replace") as f:
        make_csv = f.read()
        csv_to_list = make_csv.split('\n')
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


def artists_to_csv(all_artists) -> list:
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
    return(result)
