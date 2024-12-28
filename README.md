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

#### Docker

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
#### Unraid

Install Python/PIP using either Nerd-tools Plugin (Unraid 6), Python 3 for UNRAID Plugin (Unraid 6 or 7), or manually via command line.

See the installation instructions [here](https://digitalec.github.io/deemon/docs/installation.html) or install as root (**NOT** recommended!):

```bash
pip install deemon
```
Then:
```bash
deemon --init
```

If deemon is not found in your path, you can also call it as a python module:
```bash
python3 -m deemon --init
```       
If installed using the **root** account, the config.json will be located at: **/root/.config/deemon/config.json**. Edit your configuration using the documentation located [here](https://digitalec.github.io/deemon/docs/configuration.html).

Use `deemon monitor -h` for help on adding artists, playlists, or albums to monitor for new releases.

#### Installation in a Python Virtual Environment (venv)

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

### Getting Started
You have to manually add artists, playlists, albums, etc.. deemon does not automatically pull artists unless they're being monitored. Refer to the documentation [here](https://digitalec.github.io/deemon/docs/commands/monitor.html).
