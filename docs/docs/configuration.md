---
layout: default
title: Configuration
nav_order: 1
---

# Configuration
{: .no_toc }


deemon has some specific configuration parameters that can be defined in your config.json file.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Configuration Location
Depending on your operating system, your config.json file will be located in one of the locations below. When deemon 
is run with a command, it will automatically generate a default config if an existing configuration file is not present.
For example: to generate this configuration file, run `deemon refresh`.

- **Linux**: /home/user/.config/deemon

- **macOS**: /User/user/Library/Application Support/deemon

- **Windows**: %appdata%\deemon

### Default Configuration (v2.0+)
```json
{
    "check_update": 1,
    "release_channel": "stable",
    "query_limit": 5,
    "rollback_view_limit": 10,
    "prompt_duplicates": false,
    "prompt_no_matches": true,
    "new_releases": {
        "by_release_date": true,
        "release_max_age": 90
    },
    "global": {
        "bitrate": "320",
        "alerts": false,
        "record_type": "all",
        "download_path": "",
        "email": ""
    },
    "deemix": {
        "path": "",
        "arl": ""
    },
    "smtp_settings": {
        "server": "",
        "port": 465,
        "username": "",
        "password": "",
        "from_addr": ""
    },
    "plex": {
        "base_url": "",
        "token": "",
        "library": ""
    }
}
```

## Configuration Types

There are technically three different "levels" of configuration in deemon. The first level is the "global" 
configuration, the second level is the "profile" configuration and the third level is the "per-artist" configuration.

### Global Configuration
The global configuration is defined inside the `config.json` configuration file. You can specify the bitrate for 
downloads, whether or not to enable notification alerts for new releases, the email address for those alerts, the type 
of releases to get and where to save downloads.

### Profile Configuration _(optional)_
Within deemon, you can configure multiple profiles (using the `profile` command) which monitors their own sets of 
artists and can use settings that override the _Global Configuration_ while inheriting the settings that are not 
defined. You can also think of these profiles as separate users.

For example, if you create a new profile and only specify a download path, that profile will inherit the other settings 
from the _Global Configuration_.

### Per-Artist Configuration _(optional)_
Within deemon, you can configure different settings for each individual artist (using the `config` command). This gives 
you the flexibility to disable alerts for certain artists or specify a certain release type, bitrate or download path.

<br>

## Global Configuration
### General Settings
**check_update**
- This option allows you to specify how frequently (in days) to check for new updates to deemon. To disable checking for 
updates, change this to `0`.

**release_channel** - _{stable | beta}_
- This option allows you to choose what updates you are notified about.

**query_limit**
- This option allows you to specify how many results are displayed when using the `search` command or when prompted 
using the `monitor` command (see _prompt_duplicates_ and _prompt_no_matches_ below).

**rollback_view_limit**
- This option allows you to specify the maximum number of transactions to display using the `rollback` command

**prompt_duplicates** _{true | false}_
- When adding a new artist using the `monitor` command, deemon will choose the highest ranked artist in situations 
where two artists have identical names. Instead, you can set this option to `true` which will prompt you with choices 
including the latest release from each artist to help you better decide which is the artist you're looking for.

**prompt_no_matches** _{true | false}_
- When adding a new artist using the `monitor` command, if deemon does not find an **exact** match for the artist 
you're searching for, it will prompt you with a list of results returned from the Deezer API.

---

### New Release Settings
**by_release_date** _{true | false}_
- By default, deemon uses the release date to determine if the release is actually new. If instead you want to capture 
_all_ releases, set this to false. Keep in mind, sometimes Deezer adds back catalogue which can result in old releases 
being flagged as new.

**release_max_age**
- This option is used when _by_release_date_ is set to `true`. This lets you control how far back to consider a new 
release 'new' from it's actual release date. This setting is helpful if you only run a `refresh` monthly or if there is 
a delay in Deezer adding a release to their catalogue.

---

### Global Settings
These settings can be overriden within deemon using _profiles_ or by specifying a _per-artist configuration_.

**bitrate** _{128 | 320 | FLAC}_
- This option allows you to specify the bitrate used for downloads.

**alerts** _{true | false}_
- Enable or disable email notification alerts when new releases are present. You must also have your email settings 
configured below (see _[SMTP Settings](#smtp-settings)_)

**record_type** _{all | album | ep | single}_
- This option allows you to specify what release types you wish to download upon release. Keep in mind, most EPs are 
labelled as albums in the Deezer API.

**download_path**
- This option allows you to specify where downloads are saved. If no path is provided, downloads will be saved in 
default deemix download directory.


- **Windows Users:** When providing a path, you **must** use double backslashes: C:\\\Music or forward slashes: C:/Music.

**email**
- This option allows you to specify an email address at which to receive alert notifications.

---

### deemix Settings
**path**
- By default, this will point to the default config directory for deemix. If your config folder is stored in a custom 
location or you've used deemix with the `--portable` option, specify that path here.

**arl**
- This is your authorization token required by `deemix` authenticate your Deezer account. This is stored in a cookie in 
your browser after logging in to Deezer.

---

### SMTP Settings
**server**
- Server address for your mail server

**port**
- Port used to connect to your mail server (typically 587 or 465)

**username**
- Username required to login to your mail server

**password**
- Password used to authenticate your account with your mail server

**from_addr**
- This is the email address your mail is to be sent from and must be a real address associated with your account 
on your mail server.

---

### Plex Settings
deemon can automatically refresh your Plex library for you after downloads are complete.

**base_url**
- This is the URL to reach your Plex server

**token**
- Authentication token required to connect to your Plex server


- For instructions on how to find your token, [click here](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

**library**
- The name of library on your Plex server to be refreshed