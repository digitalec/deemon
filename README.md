# deemon


### About
deemon is an automation tool that relies on the deemix library and
the deezer-py API module to monitor a specified list of artists for new releases

### Prerequisites
* python >= 3.6
* deemix >= 2.0.1
* deezer-py > 0.0.15

### Installation

```pip install deemon```

You may want to add an entry in your crontab to run this weekly _(e.g. every Friday at 06:00)_:

```0    6   *   *   5   /home/user/.local/bin/deemon -f artists.txt```

### Usage
```
deemon --input <file|dir\> [ --output <dir\> ] [ --config <dir\> ] [ --bitrate < 1 | 3 | 9 > ]
```

By default, deemon uses the default paths for the config and download directories
provided by deemix to make getting started easier.

* **-i, --input**
  * Path to text file containing list of artists -or- path to parent directory of artist subdirectories


* **-o, --output**
  * Path to save new releases
  * **Default:** _~/Music/deemix Music_
    

* **-c, --config**
  * Path to deemix config directory
  * **Default:** _~/.config/deemix_
    

* **-b, --bitrate**
  * **1** - MP3 128kbps
  * **3** - MP3 320kbps **(Default)**
  * **9** - FLAC