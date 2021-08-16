<img src="deemon/assets/images/deemon.png" alt="deemon" width="300">

[About](#about) | [Installation](#installation) | [Docker](#docker) | [Documentation](https://digitalec.github.io/deemon) | [Support](#support)

![PyPI](https://img.shields.io/pypi/v/deemon?style=flat)
[![Downloads](https://pepy.tech/badge/deemon)](https://pepy.tech/project/deemon)
![GitHub last commit](https://img.shields.io/github/last-commit/digitalec/deemon?style=flat)
![GitHub last release](https://img.shields.io/github/release-date/digitalec/deemon?style=flat)
![Discord](https://img.shields.io/discord/831356172464160838?style=flat)
![Docker](https://img.shields.io/github/workflow/status/digitalec/deemon/Deploy%20Docker?style=flat-square)


### About
deemon is a command line tool written in Python that monitors artists for new releases, provides email notifications and can also integrate with the deemix library to automatically download new releases.

### Support
[Open an Issue](https://github.com/digitalec/deemon/issues/new) | [Discord](https://discord.gg/KzNCG2tkvn)

### Installation

#### Using pip

```bash
$ pip install deemon
```

#### From source
```bash
$ pip install -r requirements.txt
$ python3 -m deemon
```

### Docker
Docker support has been added for `amd64`, `arm64` and `armv7` architectures. It is recommended to save your `docker run` command as a script to execute via cron/Task Scheduler.

**Note:** Inside deemon's `config.json`, download_location **must** be set to `/downloads` until I can integrate this myself.

**Example: Monitoring a directory of artists**
```
docker run --name deemon \
       --rm \
       -v /path/to/deemon/config:/config \
       -v /path/to/music:/downloads \
       -v /path/to/deemix/config:/deemix  \
       -v /path/to/monitor:/import \
       ghcr.io/digitalec/deemon:latest \
       python3 -m deemon import /import
```

**Example: Monitoring a file of artists**
```
docker run --name deemon \
       --rm \
       -v /path/to/deemon/config:/config \
       -v /path/to/music:/downloads \
       -v /path/to/deemix/config:/deemix  \
       -v /file/to/monitor:/artists.txt \
       ghcr.io/digitalec/deemon:latest \
       python3 -m deemon import /artists.txt
```


Default `config.json`:
```json
{
    "plex_baseurl": "",
    "plex_token": "",
    "plex_library": "",
    "download_path": "/downloads",
    "deemix_path": "",
    "arl": "",
    "release_by_date": 1,
    "release_max_days": 90,
    "bitrate": 3,
    "alerts": 0,
    "record_type": "all",
    "smtp_server": "",
    "smtp_port": 465,
    "smtp_user": "",
    "smtp_pass": "",
    "smtp_sender": "",
    "smtp_recipient": ""
}
```
