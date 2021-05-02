from pathlib import Path
import json


class Config:

    def __init__(self, config_path):
        self.config = {"smtp_server": "", "smtp_port": 465, "smtp_username": "", "smtp_password": "",
                       "smtp_recipient": "", "smtp_sender_email": ""}
        self.config_file = config_path + "/deemon/config.json"
        self.load_config()

    def load_config(self):
        if not Path(self.config_file).is_file():
            with open(self.config_file, 'w+') as f:
                json.dump(self.config, f, indent=4)

        with open(self.config_file) as f:
            data = json.load(f)

        self.config["smtp_server"] = data.get('smtp_server')
        self.config["smtp_port"] = data.get('smtp_port')
        self.config["smtp_username"] = data.get('smtp_username')
        self.config["smtp_password"] = data.get('smtp_password')
        self.config["smtp_recipient"] = data.get('smtp_recipient')
        self.config["smtp_sender_name"] = data.get('smtp_sender_name')
        self.config["smtp_sender_email"] = data.get('smtp_sender_email')
