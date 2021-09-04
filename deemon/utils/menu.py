import logging

from deemon.core.config import Config
from deemon.core.db import Database
from deemon.utils.dates import get_year
from deemon.utils import startup
from deemon.cmd import monitor

logger = logging.getLogger(__name__)


class Menu(object):
    def __init__(self, question: str, choices: list, artist_id: int = None):
        self.__choices: list = choices
        self.filtered_choices: list = self.__choices.copy()
        self.question: str = question
        self.filter: str = None
        self.sort: str = None
        self.desc: bool = True
        self.config = Config()
        self.artist_id = artist_id
        self.db = Database()

    def display_menu(self):
        print(self.question)
        if self.desc:
            sort_text = str(self.sort) + " (desc)"
        else:
            sort_text = str(self.sort) + " (asc)"

        print("Filter: " + str(self.filter) + " | Sort By: " + sort_text + "\n")
        self.filtered_choices = self.filter_choices(self.filter)
        self.filtered_choices = sorted(self.filtered_choices, key=lambda x: x[self.sort], reverse=self.desc)
        for idx, option in enumerate(self.filtered_choices, start=1):
            print(f"{idx}. ({get_year(option['release_date'])}) {option['title']}")
        print("")

    def get_album_menu(self):
        self.sort = 'release_date'
        user_choice: int = None
        while (user_choice) not in range(len(self.filtered_choices)):
            artist_monitored = self.db.get_monitored_artist_by_id(self.artist_id)
            self.display_menu()
            print("Filters: (*) All  (a) Albums  (e) EP  (s) Singles")
            print("Sort: (y) Year Desc  (Y) Year Asc  (t) Title Desc  (T) Title Asc")
            if not artist_monitored:
                print("Options: (d) Download Listed  (m) Monitor Artist\n")
            else:
                print("Options: (d) Download Listed  (m) Stop Monitoring Artist\n")
            prompt = input("Please choose an option or press Enter to quit: ")
            print("")
            if prompt in ['*', 'a', 'e', 's']:
                if prompt.lower() == "a":
                    self.filter = "album"
                elif prompt.lower() == "e":
                    self.filter = "ep"
                elif prompt.lower() == "s":
                    self.filter = "single"
                else:
                    self.filter = None
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
            elif prompt == "d":
                return self.filtered_choices
            elif prompt == "m":
                if artist_monitored:
                    stop = True
                else:
                    stop = False

                record_type = self.filter or self.config.record_type()

                self.clear()
                monitor.monitor("artist_id", self.artist_id, self.config.bitrate(),
                                record_type, self.config.alerts(),
                                remove=stop, dl_obj=None)
            elif prompt == "":
                return
            else:
                try:
                    prompt = int(prompt)
                    user_choice = prompt - 1
                    return [self.filtered_choices[user_choice]]
                except (ValueError, IndexError):
                    continue
            self.clear()

    def filter_choices(self, filter_by):
        filtered = self.__choices
        if filter_by in ['album', 'ep', 'single']:
            filtered = [x for x in filtered if x['record_type'] == self.filter]
        return filtered

    def clear(self):
        from os import system, name
        if name == 'nt':
            _ = system('cls')
        else:
            _ = system('clear')

    def show_artist_menu(self):
        print(self.question)
        for idx, option in enumerate(self.filtered_choices, start=1):
            print(f"{idx}. {option['name']}")
        print("")

    def gen_artist_menu(self):
        self.sort = 'name'
        user_choice: int = None
        while (user_choice) not in range(len(self.filtered_choices)):
            self.show_artist_menu()
            prompt = input("Please choose an option or press Enter to quit: ")
            print("")
            if prompt == "":
                return
            else:
                try:
                    prompt = int(prompt)
                    user_choice = prompt - 1
                    self.clear()
                    return [self.filtered_choices[user_choice]]
                except (ValueError, IndexError):
                    self.clear()
                    continue