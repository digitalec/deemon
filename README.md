# deemon
![PyPI](https://img.shields.io/pypi/v/deemon?style=flat-square)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/deemon?style=flat-square)
![PyPI - License](https://img.shields.io/pypi/l/deemon?style=flat-square)
![PyPI - Status](https://img.shields.io/pypi/status/deemon?style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dm/deemon?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/digitalec/deemon?style=flat-square)


[About](#about) **|** [Prerequisites](#prerequisites) **|** [Installation](#installation) **|** [Usage](#usage) **|** [Examples](#examples)


### About
deemon is an automation tool that relies on the deemix library and
the deezer-py API module to monitor a specified list of artists for new releases


### Prerequisites
* python >= 3.6
* deemix >= 2.0.1

### Installation

```$ pip install deemon```

You may want to add an entry in your crontab to run this weekly _(e.g. every Friday at 06:00)_:

```0    6   *   *   5   /home/USER/.local/bin/deemon -a artists.txt -m /plex/music```

### Usage
```
$ deemon -a <file|dir\> [ -m <dir\> ] [ -c <dir\> ] [ -b < 1 | 3 | 9 > ] [ -d <dir\> ]
```

By default, deemon uses the default paths for the config and download directories
provided by deemix to make getting started easier.

* **-a** _/path/to/file.txt_ _**or**_ _/path/to/artists..._

    * ***Required*** - Path to text file containing _one artist per line_ -or- path to parent directory containing artist subdirectories


* **-m** _/path/to/music_

    * ***Optional*** - Path to download new releases
    * _Default: ~/Music/deemix Music_
    

* **-c** _/path/to/config_

    * ***Optional*** - Path to deemix config directory
    * _Default: ~/.config/deemix_
    

* **-b** _int_

    * ***Optional*** - Set bitrate
    * **1** - MP3 128kbps
    * **3** - MP3 320kbps **(Default)**
    * **9** - FLAC


* **-d** _/path/to/database_

    * ***Optional*** - Path to save database
    * _Default: ~/.config/deemon_

### Examples
In the examples below, my music library structure is as follows:
```
plex/
   music/
      Artist 1/
      Artist 2/
```

#### Method A - Use a text file containing one artist per line, download to _/plex/music_ as FLAC:
_This method is good for monitoring only specific artists_

```
$ deemon -a artists.txt -m /plex/music -b 9
```

```
$ cat artists.txt
Artist 1
Artist 2
Artist 3
```

#### Method B - Use a directory containing subdirectory for each artists; download to _/plex/music_:
_This method is good for monitoring all artists_

```
$ deemon -a /plex/music -m /plex/music
```

```
$ ls /plex/music
Artist 1/
Artist 2/
Artist 3/
```
