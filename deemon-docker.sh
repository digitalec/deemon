if [ -f /_config/artists.txt ]; then
	echo -e "@reboot python3 -m deemon import /config/artists.txt\n" \
	"0 6 * * * python3 -m deemon import /config/artists.txt\n" \
	"0 12 * * * python3 -m deemon import /config/artists.txt" | crontab -u deemon -
else
	echo -e "@reboot python3 -m deemon refresh\n" \
	"0 6 * * * python3 -m deemon refresh\n" \
	"0 12 * * * python3 -m deemon refesh" | crontab -u deemon -
fi

crond -f
