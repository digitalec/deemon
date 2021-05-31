import smtplib
import ssl
import logging
from email.utils import formataddr
from email.message import EmailMessage

logger = logging.getLogger("deemon")


class EmailNotification:

    def __init__(self, config):
        self.config = config
        self.enable_notify = True if self.config["smtp_server"] != "" else False

    def notify(self, new_releases=[], test=False):
        if test:
            message = "Congrats! You'll now receive new release notifications."
            subject = "deemon Test Notification"
        elif self.enable_notify:
            message = "The following new releases were detected:\n"
            subject = "New release(s) detected!"
            for release in new_releases:
                message = message + "\n" + release
            msg = EmailMessage()
            msg['From'] = formataddr(('deemon', self.config["smtp_sender_email"]))
            msg['Subject'] = subject
            msg['To'] = self.config["smtp_recipient"]
            msg.set_content(message)

            context = ssl.create_default_context()

            logger.debug("Sending new release notification email")
            logger.debug(f"Using server: {self.config['smtp_server']}:{self.config['smtp_port']}")
            with smtplib.SMTP_SSL(self.config["smtp_server"], self.config["smtp_port"], context=context) as server:
                try:
                    server.login(self.config["smtp_username"], self.config["smtp_password"])
                    server.sendmail(self.config["smtp_sender_email"], self.config["smtp_recipient"], msg.as_string())
                except Exception as e:
                    logger.error("Error while sending mail: " + str(e))
