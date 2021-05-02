from pathlib import Path
import json
import smtplib
import ssl
from email.utils import formataddr
from email.message import EmailMessage


class EmailNotification:

    def __init__(self, config):
        self.config = config

    def notify(self, new_releases):
        message = "The following new releases were detected:\n"
        for release in new_releases:
            message = message + "\n" + release
        msg = EmailMessage()
        msg['From'] = formataddr(('deemon', self.config["smtp_sender_email"]))
        msg['Subject'] = "New release(s) detected!"
        msg['To'] = self.config["smtp_recipient"]
        msg.set_content(message)

        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(self.config["smtp_server"], self.config["smtp_port"], context=context) as server:
            server.login(self.config["smtp_username"], self.config["smtp_password"])
            server.sendmail(self.config["smtp_sender_email"], self.config["smtp_recipient"], msg.as_string())
