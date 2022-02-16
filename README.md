<img src="deemon/assets/images/deemon.png" alt="deemon" width="300">

[About](#about) | [Installation](#installation) | [Docker](#docker) | [Documentation](https://digitalec.github.io/deemon) | [Support](#support)

![PyPI](https://img.shields.io/pypi/v/deemon?style=flat)
[![Downloads](https://pepy.tech/badge/deemon)](https://pepy.tech/project/deemon)
![GitHub last commit](https://img.shields.io/github/last-commit/digitalec/deemon?style=flat)
![GitHub last release](https://img.shields.io/github/release-date/digitalec/deemon?style=flat)
![Discord](https://img.shields.io/discord/831356172464160838?style=flat)
![Docker](https://img.shields.io/github/workflow/status/digitalec/deemon/Deploy%20Docker?style=flat)
[![Donate](https://img.shields.io/badge/Donate-PayPal-blue?style=flat&logo=paypal)](https://paypal.me/digitalec)


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

**Docker support will be removed in the next major release. It is recommended to use a python virtual environment
instead ([see below](#installation-in-a-python-virtual-environment-venv)).**

Docker support has been added for `amd64`, `arm64` and `armv7` architectures. It is recommended to save your `docker run` command as a script to execute via cron/Task Scheduler.

**Note:** Inside deemon's `config.json`, download_location **must** be set to `/downloads` until I can integrate this myself.

**Example: Monitoring a file of artists**
```
docker run --name deemon \
       --rm \
       -v /path/to/deemon/config:/config \
       -v /path/to/music:/downloads \
       -v /path/to/deemix/config:/deemix  \
       -v /file/to/monitor:/artists.txt \
       ghcr.io/digitalec/deemon:latest \
       python3 -m deemon monitor --import /artists.txt
```

### Installation in a Python Virtual Environment (venv)

If you wish to install deemon and it's dependencies in a sandbox-style environment, I would recommend using venv.

Create a venv and install deemon
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

### Default Configuration
If you need to generate a new default configuration, please rename or delete your current `config.json`. The
configuration will be generated the next time you run deemon.
