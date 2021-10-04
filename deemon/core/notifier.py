import logging
import platform
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

import pkg_resources

from deemon import __version__
from deemon.core.config import Config as config

logger = logging.getLogger(__name__)


class Notify:

    def __init__(self, new_releases: list = None):
        logger.debug("notify initialized")
        logger.debug(f"releases to notify on: {new_releases}")
        self.subject = "New releases detected!"
        self.releases = new_releases

    def send(self, body=None, test=False, expired=False):
        """
        Send email notification message
        """
        if not all([config.smtp_server(), config.smtp_port(), config.smtp_user(),
                    config.smtp_pass(), config.smtp_sender(), config.smtp_recipient()]):
            if test:
                logger.info("Unable to send test notification, email is not configured")
            logger.debug("Email not configured, no notifications will be sent")
            return False

        if not body:
            body = self.build_message()

        context = ssl.create_default_context()

        logger.debug("Sending notification email")
        logger.debug(f"Using server: {config.smtp_server()}:{config.smtp_port()}")

        with smtplib.SMTP_SSL(config.smtp_server(), config.smtp_port(), context=context) as server:
            try:
                server.login(config.smtp_user(), config.smtp_pass())
                server.sendmail(config.smtp_sender(), config.smtp_recipient(), body.as_string())
                logger.debug("Email notification has been sent")
            except Exception as e:
                logger.error("Error while sending mail: " + str(e))

    def get_cover_images(self):
        pass

    def build_message(self):
        """
        Builds message by combining plaintext and HTML messages for sending
        """
        msg = MIMEMultipart('mixed')
        msg['To'] = config.smtp_recipient()
        msg['From'] = formataddr(('deemon', config.smtp_sender()))
        msg['Subject'] = self.subject
        # part1 = MIMEText(self.plaintext(), 'plain')
        part2 = MIMEText(self.html_new_releases(), 'html')
        # msg.attach(part1)
        msg.attach(part2)

        return msg

    def test(self):
        """
        Verify SMTP settings by sending test email
        """
        self.subject = "deemon Test Notification"
        message = "Congrats! You'll now receive new release notifications."
        msg = EmailMessage()
        msg['To'] = config.smtp_recipient()
        msg['From'] = formataddr(('deemon', config.smtp_sender()))
        msg['Subject'] = self.subject
        msg.set_content(message)
        self.send(msg, test=True)

    def expired_arl(self):
        """
        Verify SMTP settings by sending test email
        """
        self.subject = "deemon Notification"
        message = "Your ARL has expired"
        msg = EmailMessage()
        msg['To'] = config.smtp_recipient()
        msg['From'] = formataddr(('deemon', config.smtp_sender()))
        msg['Subject'] = self.subject
        msg.set_content(message)
        self.send(msg, test=True)

    def plaintext(self) -> str:
        """
        Plaintext version of email to send
        """
        message = "The following new releases were detected:\n\n"
        for release in self.releases:
            release_date_ts = datetime.strptime(release["release_date"], "%Y-%m-%d")
            release_date_str = datetime.strftime(release_date_ts, "%A, %B %-d")
            message += f"\n{release_date_str}\n"
            for album in release["releases"]:
                message += f"+ {album['artist']} - {album['album']}\n"
        return message

    def html_new_releases(self):

        app_version = f"deemon {__version__}"
        py_version = f"python {platform.python_version()}"
        sys_version = f"{platform.system()} {platform.release()}"

        new_release_list_spacer = f"""
            </ul>
            <p style="font-size: 14px; line-height: 140%;">&nbsp;</p>
        """

        all_new_releases = ""

        self.releases = sorted(self.releases, key=lambda x: x['release_date'], reverse=True)

        for release in self.releases:

            if all_new_releases != "":
                all_new_releases += new_release_list_spacer

            release_date_ts = datetime.strptime(release["release_date"], "%Y-%m-%d")
            release_date_str = datetime.strftime(release_date_ts, "%A, %B %d").replace(" 0", " ")

            new_release_list_header = f"""
                <p style="font-size: 14px; line-height: 140%;">
                    <strong>
                        <span style="font-size: 16px; line-height: 22.4px;">{release_date_str}</span>
                    </strong>
                </p>
                <ul>
            """

            new_release_list_item = ""

            for album in release["releases"]:
                new_release_list_item += f"""
                        <li style="font-size: 14px; line-height: 19.6px;">
                            <span style="font-size: 16px; line-height: 22.4px;">
                                {album['artist']} - {album['album']}
                            </span>
                        </li>
                """

            all_new_releases += new_release_list_header + new_release_list_item

        index = pkg_resources.resource_filename('deemon', 'assets/index.html')
        with open(index, 'r') as f:
            html_output = f.read()

            if config.update_available():
                html_output = html_output.replace("{UPDATE_MESSAGE}", "A new update is available!")
            else:
                html_output = html_output.replace("{UPDATE_MESSAGE}", "")
                html_output = html_output.replace("{VIEW_UPDATE_MESSAGE}", "display:none;")

            html_output = html_output.replace("{NEW_RELEASE_LIST}", all_new_releases)
            html_output = html_output.replace("{DEEMON_VER}", app_version)
            html_output = html_output.replace("{PY_VER}", py_version)
            html_output = html_output.replace("{SYS_VER}", sys_version)

        return html_output
