from pathlib import Path

import tqdm as tqdm
from deezer import Deezer


def read_album_ids_from_file(filename):
    if not Path(filename).exists():
        raise Exception("File does not exist")
    ids = []
    with open(filename, 'r') as f:
        f.readline()
        for l in f:
            ids.append(l.encode("ascii", "ignore"))
        print("Total lines read from text file: " + str(len(ids)))
        return ids


def clean_absolute_paths(album_list):
    stripped = []
    for line in album_list:
        stripped.append(line.split("\\"))
    return stripped


def clean_year_from_album(album_list, level: int = 5):
    artist_album = []
    for line in album_list:
        if len(line) == level:
            strip_year = line[3][-6:].strip("()")
            try:
                int(strip_year)
            except Exception:
                artist_album.append([line[2], line[3]])
                continue
            artist_album.append([line[2], line[3][:-6]])
    return artist_album


def clean_artist_album_text(album_list: list):
    stripped = []
    for line in album_list:
        line = line.decode()
        line = line.replace('\n', '')
        line = line.replace('�', '')
        line = line.replace('¡', '')
        line = line.replace('É', 'E')
        line = line.replace('.', '')
        line = line.replace('+', ' ')
        line = line.replace('/', ' ')
        stripped.append(line.split(" - "))
    return stripped


def get_artist_album(filename: str, absolute_path: bool = False):
    list_from_file = read_album_ids_from_file(filename)
    if absolute_path:
        stripped_paths = clean_absolute_paths(list_from_file)
        artist_album = clean_year_from_album(stripped_paths, level=5)
    else:
        artist_album = clean_artist_album_text(list_from_file)
    print("Total albums to lookup: " + str(len(artist_album)))
    return sorted(x for x in artist_album)


def get_api_results(album_list, artist_name: str = None):
    dz = Deezer()

    for x in album_list:
        album_list.set_description_str(f"Pass: {str(len(id_list))} | Fail: {str(len(fail_list))}")
        # For testing, only process this artist
        if artist_name and artist_name != x[0]:
            continue
        # Remove things like "(Bonus Tracks)"
        artist_from_file = x[0]
        album_from_file = x[1]
        stripped_album_from_file = x[1].split(" (")[0]

        api_artist = dz.api.search_artist(x[0], limit=10)['data']
        found_artist = True
        for artist_result in api_artist:
            # TODO name decode - replace unknown with ? - use as wildcard
            encoded_name = artist_result['name'].encode("ascii", "replace")
            decoded_name = encoded_name.decode()
            if artist_from_file == decoded_name:
                api_artist = artist_result
                found_artist = True
                break
            else:
                found_artist = False

        # TODO make this add albums to id and break out
        if found_artist is False:
            for artist in api_artist:
                get_albums = dz.api.get_artist_albums(artist['id'])['data']
                if album_from_file in [x['title'] for x in get_albums]:
                    api_artist = artist
                    break
            #
            # print("Searched all albums, nothing matches!")
            # exit()
        try:
            all_albums = dz.api.get_artist_albums(api_artist['id'])['data']
        except:
            fail_list.append(f"{x[0]} - {x[1]}")
            continue
        api_albums = [[x['title'].split(" (")[0], x['id']] for x in all_albums]
        for [title, id] in api_albums:
            clean_title = title
            clean_title = clean_title.replace('¡', '')
            clean_title = clean_title.replace('É', 'E')
            clean_title = clean_title.replace('.', '')
            clean_title = clean_title.replace(' + ', ' ')
            clean_title = clean_title.replace(' / ', ' ')
            if album_from_file.lower() == clean_title.lower() or stripped_album_from_file.lower() == clean_title.lower():
                if id not in id_list:
                    id_list.append(id)
                break
            if album_from_file.lower() in clean_title.lower() or stripped_album_from_file.lower() in clean_title.lower():
                if id not in id_list:
                    id_list.append(id)
                break
        else:
            fail_list.append(f"{x[0]} - {x[1]}")


id_list = []
fail_list = []
input_file_or_directory: str = None
output_file_passing: str = None
output_file_failing: str = None

album_list = get_artist_album(input_file_or_directory)

progress = tqdm.tqdm(album_list, ascii=" #",
                     bar_format='{desc}...  {n_fmt}/{total_fmt} [{bar:40}] {percentage:3.0f}%')
progress.set_description_str("Getting IDs")

get_api_results(progress)

print("PASS: " + str(len(id_list)))
with open(output_file_passing, "w") as f:
    for id in id_list:
        f.write(str(id) + "\n")

print("FAIL: " + str(len(fail_list)))
with open(output_file_failing, "w") as f:
    for id in fail_list:
        f.write(str(id) + "\n")
