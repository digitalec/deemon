<img src="deemon/assets/images/deemon.png" alt="deemon" width="300">

[About](#about) | [Installation](#installation) | [Docker](#docker) | [Documentation](https://digitalec.github.io/deemon) | [Support](#support)

![PyPI](https://img.shields.io/pypi/v/deemon?style=for-the-badge)
![Downloads](https://img.shields.io/pepy/dt/deemon?style=for-the-badge)
![GitHub last release](https://img.shields.io/github/release-date/digitalec/deemon?style=for-the-badge)

![GitHub last commit](https://img.shields.io/github/last-commit/digitalec/deemon?style=for-the-badge)
![Docker](https://img.shields.io/github/actions/workflow/status/digitalec/deemon/deploy-docker.yml?branch=main&style=for-the-badge&logo=docker)

![Discord](https://img.shields.io/discord/831356172464160838?style=for-the-badge&logo=discord)


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

**Example: Refreshing an existing database**
```
docker run --name deemon \
       --rm \
       -v /path/to/deemon/config:/config \
       -v /path/to/music:/downloads \
       -v /path/to/deemix/config:/deemix  \
       ghcr.io/digitalec/deemon:latest \
       python3 -m deemon refresh
```
### Unraid

Install Python/PIP using either Nerd-tools Plugin (Unraid 6), Python 3 for UNRAID Plugin (Unraid 6 or 7), or manually via command line.

Run: (or see the Python venv section)
```bash
pip install deemon
```
Then:
```bash
deemon refresh
```
or
```bash
python3 -m deemon refresh
```
This will generate the default config.json

Edit the global config.json located in **/root/.config/deemon/config.json**

Example:
```commandline
{
    "check_update": 1,
    "debug_mode": false,
    "release_channel": "stable",
    "query_limit": 5,
    "smart_search": true,
    "rollback_view_limit": 10,
    "prompt_duplicates": false,
    "prompt_no_matches": true,
    "fast_api": true,
    "fast_api_threads": 25,
    "exclusions": {
        "enable_exclusions": true,
        "patterns": [],
        "keywords": []
    },
    "new_releases": {
        "release_max_age": 90,
        "include_unofficial": false,
        "include_compilations": false,
        "include_featured_in": false
    },
    "global": {
        "bitrate": "flac",                        #128, 320, flac
        "alerts": false,                          
        "record_type": "all",                     #all, album, ep, single
        "download_path": "/Your/Path/To/Music/",  #Example: /mnt/user/Share/media/Music/
        "email": ""
    },
    "deemix": {
        "path": "/Your/Path/to/deemix/",          #Example: /mnt/user/appdata/deemix/
        "arl": "YourDeezerARL"                    #Copy from Deemix
        "check_account_status": true,
        "halt_download_on_error": false
    },
    "smtp_settings": {
        "server": "",
        "port": 465,
        "starttls": false,
        "username": "",
        "password": "",
        "from_addr": ""
    },
    "plex": {
        "base_url": "https://yourplexip:32400",
        "ssl_verify": true,
        "token": "YourPlextoken",           #Google how to obtain your Plex Token
        "library": "YourMusic"              #Name of your Plex Music Library, most likely 'Music'
    },
    "profile_id": 1,
    "tid": 0
}
```

Use ```deemon monitor -h``` for help on adding artists, playlists, or albums to monitor for new releases.


### Installation in a Python Virtual Environment (venv)

If you wish to install deemon and it's dependencies in a sandbox-style environment, I would recommend using venv.

Create a venv and install deemon (you may need to use `python3` and `pip3` depending on your system):
```commandline
$ python -m venv venv
$ source ./venv/bin/activate
$ pip install deemon
```

When you are finished, close the terminal or exit our venv:
```commandline
$ deactivate
```

Next time you want to run deemon, activate the venv first:
```commandline
$ source ./venv/bin/activate
$ deemon refresh
```

If you are moving to venv from the Docker container, be sure to update your cron/Task Scheduler scripts.

### IMPORTANT!!
You have to manually add artists, playlists, albums, etc.. Deemon does not automatically pull artists from Deemix.
Example:

```deemon monitor Post Malone```

```deemon monitor -p https://www.deezer.com/us/playlist/2228601362```

### Default Configuration
If you need to generate a new default configuration, please rename or delete your current `config.json`. The
configuration will be generated the next time you run deemon.
