# deemon


### About
deemon is an automation tool that relies on the deemix library and
the deezer-py API module to monitor a specified list of artists for new releases

### Prerequisites
* python >= 3.6
* deemix >= 2.0.1

### Installation

```pip install deemon```

You may want to add an entry in your crontab to run this weekly _(e.g. every Friday at 06:00)_:

```0    6   *   *   5   /home/user/.local/bin/deemon -f artists.txt```

### Usage
```
deemon -a <file|dir\> [ -m <dir\> ] [ -c <dir\> ] [ -b < 1 | 3 | 9 > ] [ -d <dir\> ]
```

By default, deemon uses the default paths for the config and download directories
provided by deemix to make getting started easier.

* **-a** [ _/path/to/file.txt_ | _/path/..._ ]

    * ***Required*** Path to text file containing list of artists _one per line_ -or- path to parent directory of artist subdirectories


* **-m** [ _/path/to/music_ ]

    * ***Optional*** Path to save new releases
    * _Default: ~/Music/deemix Music_
    

* **-c** [ _/path/to/config_ ]

    * ***Optional*** Path to deemix config directory
    * _Default: ~/.config/deemix_
    

* **-b** [ _int_ ]

    * ***Optional*** Set bitrate
    * **1** - MP3 128kbps
    * **3** - MP3 320kbps **(Default)**
    * **9** - FLAC


* **-d** [ _/path/to/database_ ]

    * ***Optional*** Path to save database
    * _Default: ~/.config/deemon_