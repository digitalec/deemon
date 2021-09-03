import logging

logger = logging.getLogger(__name__)


class Menu(object):
    def __init__(self, question: str, choices: list):
        self.choices: list = choices
        self.question: str = question

    def display_menu(self):
        print(self.question)
        for idx, option in enumerate(self.choices, start=1):
            print(f"{idx} - {option['name']} ({option['id']})")
        print("")

    def get_user_choice(self):
        user_choice: int = None
        self.display_menu()
        while (user_choice) not in range(len(self.choices)):
            try:
                prompt = int(input("Please choose an option (or press Enter to cancel): "))
            except ValueError:
                return False
            user_choice = prompt - 1
        logger.debug(f"User chose: {self.choices[user_choice]}")
        return user_choice
