import logging
import sys

from deezer import Deezer

from deemon.cmd import download
from deemon.cmd import monitor as mon
from deemon.core import db
from deemon.core.config import Config as config
from deemon.utils import dates

logger = logging.getLogger(__name__)


class Search:
    def __init__(self):
        self.artist_id: int = None
        self.artist: str = None
        self.choices: list = []
        self.status_message: str = None
        self.queue_list = []
        self.select_mode = False
        self.explicit_only = False
        self.user_search_query: str = None

        self.sort: str = "release_date"
        self.filter: str = None
        self.desc: bool = True

        self.db = db.Database()
        self.dz = Deezer()

    @staticmethod
    def truncate_artist(name: str):
        if len(name) > 45:
            return name[0:40] + "..."
        return name

    def get_latest_release(self, artist_id: int):
        try:
            all_releases = self.dz.api.get_artist_albums(artist_id)['data']
            sorted_releases = sorted(all_releases, key=lambda x: x['release_date'], reverse=True)
            latest_release = sorted_releases[0]
        except IndexError:
            return "       - No releases found"
        return f"       - Latest release: {latest_release['title']} ({dates.get_year(latest_release['release_date'])})"

    def display_monitored_status(self, artist_id: int):
        if self.db.get_monitored_artist_by_id(artist_id):
            return "[M] "
        return "    "

    @staticmethod
    def has_duplicate_artists(name: str, artist_dicts: dict):
        names = [x['name'] for x in artist_dicts if x['name'] == name]
        if len(names) > 1:
            return True

    def show_mini_queue(self):
        num_queued = len(self.queue_list)
        if num_queued > 0:
            return f" ({str(num_queued)} Queued)"
        return ""

    def search_menu(self, query: str = None):
        exit_search: bool = False
        quick_search: bool = False
        while exit_search is False:
            self.clear()
            print("deemon Interactive Search Client\n")
            if len(self.queue_list) > 0:
                self.display_options(options="(d) Download Queue  (Q) Show Queue")
            if query:
                search_query = query
                quick_search = True
            else:
                search_query = input(f":: Enter an artist to search for{self.show_mini_queue()}: ")
                if search_query == "exit":
                    if self.exit_search():
                        sys.exit()
                    continue
                if search_query == "d":
                    if len(self.queue_list) > 0:
                        self.start_queue()
                        continue
                if search_query == "Q":
                    if len(self.queue_list) > 0:
                        self.queue_menu()
                    else:
                        self.status_message = "Queue is empty"
                    continue
                if search_query == "":
                    continue
            artist_search_result = self.dz.api.search_artist(search_query, limit=config.query_limit())['data']
            if len(artist_search_result) == 0:
                self.status_message = "No results found for: " + search_query
                continue

            artist_selected = self.artist_menu(search_query, artist_search_result, quick_search)
            if artist_selected:
                self.user_search_query = search_query
                return [artist_selected]
            elif quick_search:
                return

    def queue_menu_options(self):
        ui_options = ("(d) Download Queue  (c) Clear Queue  (b) Back")
        self.display_options(options=ui_options)

    def artist_menu(self, query: str, results: dict, artist_only: bool = False):
        exit_artist: bool = False
        while exit_artist is False:
            self.clear()
            print("Search results for artist: " + query)
            for idx, option in enumerate(results, start=1):
                print(f"{self.display_monitored_status(option['id'])}{idx}. {self.truncate_artist(option['name'])}")
                if self.has_duplicate_artists(option['name'], results):
                    print(self.get_latest_release(option['id']))
                    print("       - Artist ID: " + str(option['id']))
                    if not option.get('nb_album'):
                        option['nb_album'] = self.dz.api.get_artist(option['id'])['nb_album']
                    print("       - Total releases: " + str(option['nb_album']))
                    self.status_message = "Duplicate artists found"
            # TODO make options smarter/modular
            if len(self.queue_list) > 0:
                self.display_options(options="(b) Back  (d) Download Queue  (Q) Show Queue")
            else:
                self.display_options(options="(b) Back")
            response = input(f":: Please choose an option or type 'exit'{self.show_mini_queue()}: ")
            if response == "d":
                if len(self.queue_list) > 0:
                    self.start_queue()
                    continue
            elif response == "Q":
                if len(self.queue_list) > 0:
                    self.queue_menu()
                else:
                    self.status_message = "Queue is empty"
                continue
            elif response == "b":
                break
            elif response == "exit":
                if self.exit_search() and not artist_only:
                    sys.exit()
                else:
                    return
            elif response == "":
                continue

            try:
                response = int(response)
            except ValueError:
                self.status_message = f"Invalid selection: {response}"
            else:
                response = response - 1
                if response in range(len(results)):
                    self.artist = results[response]['name']
                    if artist_only:
                        self.clear()
                        return results[response]
                    self.album_menu(results[response])
                else:
                    self.status_message = f"Invalid selection: {response}"
                    continue

    def album_menu_header(self, artist: str):
        filter_text = "All" if not self.filter else self.filter.title()
        if self.explicit_only:
            filter_text = filter_text + " (Explicit Only)"
        desc_text = "desc" if self.desc else "asc"
        sort_text = self.sort.replace("_", " ").title() + " (" + desc_text + ")"
        print("Discography for artist: " + artist)
        print("Filter by: " + filter_text + " | Sort by: " + sort_text + "\n")

    def album_menu_options(self, monitored):
        print("")
        if not monitored:
            monitor_opt = "(m) Monitor"
        else:
            monitor_opt = "(m) Stop Monitoring"
        ui_filter = "Filters: (*) All  (a) Albums  (e) EP  (s) Singles - (E) Explicit (r) Reset"
        ui_sort = "   Sort: (y) Year Desc  (Y) Year Asc  (t) Title Desc  (T) Title Asc"
        ui_mode = "   Mode: (S) Toggle Select"
        ui_options = ("(b) Back  (d) Download Queue  (Q) Show Queue  (f) Queue Filtered  "
                      f"{monitor_opt}")
        self.display_options(ui_filter, ui_sort, ui_mode, ui_options)

    @staticmethod
    def explicit_lyrics(is_explicit):
        if is_explicit:
            return " [E]"
        else:
            return ""

    def item_selected(self, id):
        if self.select_mode:
            if [x for x in self.queue_list if x.album_id == id or x.track_id == id]:
                return "[*] "
            else:
                return "[ ] "
        else:
            return "    "

    def show_mode(self):
        if self.select_mode:
            return "[SELECT] "
        return ""

    def album_menu(self, artist: dict):
        exit_album_menu: bool = False
        artist_albums = self.dz.api.get_artist_albums(artist['id'])['data']
        while exit_album_menu is False:
            self.clear()
            self.album_menu_header(artist['name'])
            filtered_choices = self.filter_choices(artist_albums)
            for idx, album in enumerate(filtered_choices, start=1):
                print(f"{self.item_selected(album['id'])}{idx}. ({dates.get_year(album['release_date'])}) "
                      f"{album['title']} {self.explicit_lyrics(album['explicit_lyrics'])}")
            monitored = self.db.get_monitored_artist_by_id(artist['id'])
            self.album_menu_options(monitored)

            prompt = input(f":: {self.show_mode()}Please choose an option or type 'exit'{self.show_mini_queue()}: ")
            if prompt == "a":
                self.filter = "album"
            elif prompt == "e":
                self.filter = "ep"
            elif prompt == "s":
                self.filter = "single"
            elif prompt == "*":
                self.filter = None
            elif prompt == "E":
                self.explicit_only ^= True
            elif prompt == "r":
                self.filter = None
                self.explicit_only = False
                self.sort = "release_date"
                self.desc = True
            elif prompt == "y":
                self.sort = "release_date"
                self.desc = True
            elif prompt == "Y":
                self.sort = "release_date"
                self.desc = False
            elif prompt == "t":
                self.sort = "title"
                self.desc = True
            elif prompt == "T":
                self.sort = "title"
                self.desc = False
            elif prompt == "S":
                self.select_mode ^= True
            elif prompt == "m":
                if monitored:
                    stop = True
                else:
                    stop = False
                record_type = self.filter or config.record_type()
                self.clear()
                monitor = mon.Monitor()
                monitor.set_config(None, None, record_type, None)
                monitor.set_options(stop, False, False)
                monitor.artist_ids([artist['id']])
            elif prompt == "f":
                if len(filtered_choices) > 0:
                    for item in filtered_choices:
                        self.send_to_queue(item)
                else:
                    self.status_message = "No items to add"
            elif prompt == "d":
                if len(self.queue_list) > 0:
                    self.start_queue()
            elif prompt == "Q":
                if len(self.queue_list) > 0:
                    self.queue_menu()
                else:
                    self.status_message = "Queue is empty"
            elif prompt == "b":
                break
            elif prompt == "":
                self.status_message = "Hint: to exit, type 'exit'!"
                continue
            elif prompt == "exit":
                if self.exit_search():
                    sys.exit()
            else:
                try:
                    selected_index = (int(prompt) - 1)
                except ValueError:
                    self.status_message = "Invalid filter, sort or option provided"
                    continue
                except IndexError:
                    self.status_message = "Invalid selection, please choose from above"
                    continue

                if selected_index in range(len(filtered_choices)):
                    if self.select_mode:
                        selected_item = filtered_choices[selected_index]
                        self.send_to_queue(selected_item)
                        continue
                    else:
                        self.track_menu(filtered_choices[selected_index])
                else:
                    self.status_message = "Invalid selection, please choose from above"
                    continue

    def track_menu_options(self):
        ui_options = ("(b) Back  (d) Download Queue  (Q) Show Queue")
        self.display_options(options=ui_options)

    def track_menu_header(self, album):
        print("deemon Interactive Search Client")
        print(f"Artist: {self.artist}  |  Album: {album['title']}\n")

    def track_menu(self, album):
        exit_track_menu: bool = False
        track_list = self.dz.api.get_album_tracks(album['id'])['data']
        self.select_mode = True
        while not exit_track_menu:
            self.clear()
            self.track_menu_header(album)

            for idx, track in enumerate(track_list, start=1):
                print(f"{self.item_selected(track['id'])}{idx}. {track['title']}")
            self.track_menu_options()

            prompt = input(f":: {self.show_mode()}Please choose an option or type 'exit'{self.show_mini_queue()}: ")
            if prompt == "d":
                if len(self.queue_list) > 0:
                    self.start_queue()
                else:
                    self.status_message = "Queue is empty"
            elif prompt == "Q":
                if len(self.queue_list) > 0:
                    self.queue_menu()
                else:
                    self.status_message = "Queue is empty"
            elif prompt == "b":
                self.select_mode = False
                break
            elif prompt == "":
                self.status_message = "Hint: to exit, type 'exit'!"
                continue
            elif prompt == "exit":
                if self.exit_search():
                    sys.exit()
            else:
                try:
                    selected_index = (int(prompt) - 1)
                except ValueError:
                    self.status_message = "Invalid filter, sort or option provided"
                    continue
                except IndexError:
                    self.status_message = "Invalid selection, please choose from above"
                    continue

                if selected_index in range(len(track_list)):
                    selected_item = track_list[selected_index]
                    self.send_to_queue(selected_item)
                    continue
                else:
                    self.status_message = "Invalid selection, please choose from above"
                    continue

    def search_header(self):
        pass

    def queue_menu(self):
        exit_queue_list = False
        while exit_queue_list is False:
            self.clear()
            for idx, q in enumerate(self.queue_list, start=1):
                if q.album_title:
                    print(f"{idx}. {q.artist_name} - {q.album_title}")
                else:
                    print(f"{idx}. {q.artist_name} - {q.track_title}")
            print("")
            self.queue_menu_options()
            response = input(f":: Please choose an option or type exit {self.show_mini_queue()}: ")
            if response == "d":
                if len(self.queue_list) > 0:
                    self.start_queue()
                else:
                    self.status_message = "Queue is empty"
            if response == "c":
                self.queue_list = []
                break
            if response == "b":
                break
            if response == "exit":
                if self.exit_search():
                    sys.exit()
            try:
                response = int(response) - 1
            except ValueError:
                continue
            if response in range(len(self.queue_list)):
                self.queue_list.pop(response)
                if len(self.queue_list) == 0:
                    break

    def exit_search(self):
        if len(self.queue_list) > 0:
            exit_all = input(":: Quit before downloading queue? [y|N] ")
            if exit_all.lower() != 'y':
                return False
        return True

    def display_options(self, filter=None, sort=None, mode=None, options=None):
        if filter:
            print(filter)
        if sort:
            print(sort)
        if mode:
            print(mode)
        if options:
            print("")
            print(options)
        if self.status_message:
            print("** " + self.status_message + " **")
            self.status_message = None

    @staticmethod
    def clear():
        from os import system, name
        if name == 'nt':
            _ = system('cls')
        else:
            _ = system('clear')

    def filter_choices(self, choices):
        apply_filter = [x for x in choices if x['record_type'] == self.filter or self.filter is None]
        if self.explicit_only:
            apply_filter = [x for x in apply_filter if x['explicit_lyrics'] == True]
        return sorted(apply_filter, key=lambda x: x[self.sort], reverse=self.desc)

    def start_queue(self):
        self.clear()
        dl = download.Download()
        dl.queue_list = self.queue_list
        dl.download_queue()
        self.queue_list.clear()
        self.status_message = "Downloads complete"

    def send_to_queue(self, item):
        if item['type'] == 'album':
            album = {'id': item['id'], 'title': item['title'], 'link': item['link'], 'artist': {'name': self.artist}}
            for i, q in enumerate(self.queue_list):
                if q.album_id == album['id']:
                    del self.queue_list[i]
                    return
            self.queue_list.append(download.QueueItem(album=album))

        elif item['type'] == 'track':
            track = {'id': item['id'], 'title': item['title'], 'link': item['link'], 'artist': self.artist}
            for i, q in enumerate(self.queue_list):
                if q.track_id == track['id']:
                    del self.queue_list[i]
                    return
            self.queue_list.append(download.QueueItem(track=track))

        elif item.get('name'):
            pass
