import logging
import platform
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

import pkg_resources

from deemon import __version__
from deemon.core.config import Config as config

logger = logging.getLogger(__name__)


class Notify:

    def __init__(self, new_releases: list = None):
        logger.debug(f"Sending notification for {new_releases} release(s)")
        self.subject = "deemon Notification"
        self.releases = new_releases

    def send(self, body=None, test=False):
        """
        Send email notification message
        """
        if not all([config.smtp_server(), config.smtp_port(), config.smtp_user(),
                    config.smtp_pass(), config.smtp_sender(), config.smtp_recipient()]):
            if test:
                logger.info("   [!] Unable to send test notification. Please configure "
                            "email server settings and provide recipient address.")
            logger.debug("Email not configured, no notifications will be sent")
            return False

        if not body:
            body = self.html_message()

        context = ssl.create_default_context()

        logger.debug("Sending notification email")
        logger.debug(f"Using server: {config.smtp_server()}:{config.smtp_port()}")

        if config.smtp_starttls():
            with smtplib.SMTP(config.smtp_server(), config.smtp_port()) as server:
                server.starttls()
                server.login(config.smtp_user(), config.smtp_pass())
                server.sendmail(config.smtp_sender(), config.smtp_recipient(), body.as_string())
                logger.debug("Email notification has been sent")
        else:
            with smtplib.SMTP_SSL(config.smtp_server(), config.smtp_port(), context=context) as server:
                server.login(config.smtp_user(), config.smtp_pass())
                server.sendmail(config.smtp_sender(), config.smtp_recipient(), body.as_string())
                logger.debug("Email notification has been sent")

    def construct_header(self, is_plain_text=True, subject=None):
        subject = subject or self.subject

        if is_plain_text:
            message = EmailMessage()
        else:
            message = MIMEMultipart('mixed')

        message['To'] = config.smtp_recipient()
        message['From'] = formataddr(('deemon', config.smtp_sender()))
        message['Subject'] = subject
        message['Date'] = formatdate(localtime=True)

        return message

    def html_message(self):
        """
        Builds HTML messages
        """
        html_body = MIMEText(self.html_new_releases(), 'html')
        msg = self.construct_header(is_plain_text=False)
        msg.attach(html_body)
        return msg

    def test(self):
        """
        Verify SMTP settings by sending test email
        """
        msg = self.construct_header(subject="deemon Test Notification")
        msg.set_content("Congrats! You'll now receive new release notifications.")
        self.send(msg, test=True)

    def expired_arl(self):
        """
        Notify user of expired ARL
        """
        msg = self.construct_header(subject="deemon - ARL expired")
        msg.set_content("Your ARL has expired. Please update your ARL to receive new releases.")
        self.send(msg)

    def expired_sub(self):
        """
        Notify user of expired subscription
        """
        msg = self.construct_header(subject="deemon - Subscription expired")
        msg.set_content("Your Deezer subscription appears to have expired.")
        self.send(msg)

    def plaintext_message(self) -> str:
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

        new_release_count = 0
        
        for release in self.releases:

            if all_new_releases != "":
                all_new_releases += new_release_list_spacer

            release_date_ts = datetime.strptime(release["release_date"], "%Y-%m-%d")
            release_date_str = datetime.strftime(release_date_ts, "%A, %B %d").replace(" 0", " ")

            new_release_list_header = f"""
			<div class="album date">
				<span class="album date badge">
					{release_date_str}
				</span>
			</div>
            """

            new_release_list_item = ""

            for album in release["releases"]:
                new_release_count += 1
                if album['record_type'].lower() == "ep":
                    record_type = "EP"
                else:
                    record_type = album['record_type'].title()
            
                if not album['track_num']:
                    album_info = record_type
                else:
                    album_info = f"{record_type} | {album['track_num']} track(s)"
            
                new_release_list_item += f"""
            <div class="album body">
				<div class="albumart">
					<img src="{album['cover']}">
				</div>
				<div class="albuminfo">
					<div class="albumtitle">
						<a href="{album['url']}">{album['album']}</a>
					</div>
					<div>
						<div class="artistname">{album['artist']}</div>
						<span>{album_info}</span>
					</div>
				</div>
			</div>
                """

            all_new_releases += new_release_list_header + new_release_list_item

        if new_release_count > 1:
            self.subject = f"{str(new_release_count)} new releases found!"
        else:
            self.subject = f"1 new release found!"
        
        index = pkg_resources.resource_filename('deemon', 'assets/index.html')
        with open(index, 'r') as f:
            html_output = f.read()

            if config.update_available():
                html_output = html_output.replace("{UPDATE_MESSAGE}", f"Update to v{config.update_available()} is now available!")
            else:
                html_output = html_output.replace("{UPDATE_MESSAGE}", "")
                html_output = html_output.replace("{VIEW_UPDATE_MESSAGE}", "display:none;")

            html_output = html_output.replace("{NEW_RELEASE_COUNT}", str(new_release_count))
            html_output = html_output.replace("{NEW_RELEASE_LIST}", all_new_releases)
            html_output = html_output.replace("{DEEMON_VER}", app_version)
            html_output = html_output.replace("{PY_VER}", py_version)
            html_output = html_output.replace("{SYS_VER}", sys_version)

        return html_output
