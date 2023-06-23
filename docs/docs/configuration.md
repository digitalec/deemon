---
layout: default
title: Configuration
nav_order: 3
---

# Configuration
{: .no_toc }


deemon has some specific configuration parameters that can be defined in your 
config.json file.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Configuration Location
Depending on your operating system, your config.json file will be located in 
one of the locations below. When deemon is run with a command, it will 
automatically generate a default config if an existing configuration file is 
not present. For example: to generate this configuration file, run 
`deemon refresh`.

- **Linux**: /home/user/.config/deemon

- **macOS**: /User/user/Library/Application Support/deemon

- **Windows**: %appdata%\deemon

### Default Configuration (Version 2.19.2)
```json
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
        "keywords": [],
    },
    "new_releases": {
        "release_max_age": 90,
        "include_unofficial": false,
        "include_compilations": false,
        "include_featured_in": false,
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
        "arl": "",
        "check_account_status": true,
        "halt_download_on_error": false,
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
        "base_url": "",
        "ssl_verify": true,
        "token": "",
        "library": ""
    }
}
```

## Configuration Types

There are technically three different "levels" of configuration in deemon. The 
first level (and default) is the "global" configuration, the second level is 
the "profile" configuration and the third level is the "per-artist" 
configuration.

### Global Configuration

The global configuration is defined inside the `config.json` configuration 
file. This configuration is used by default when running deemon and the values 
defined in this configuration may be temporarily superseded by a 
[Profile](#profile-configuration-optional) or an 
[Artist](#per-artist-configuration-optional) configuration.

### Profile Configuration *(optional)*

Within deemon, you can configure multiple profiles (using the `profile` 
command) which monitors their own sets of artists and can use settings that 
override the _Global Configuration_ while inheriting the settings that are not 
defined. You can also think of these profiles as separate users. For example, 
if you create a new profile and only specify a download path, that profile will 
inherit the other settings from the _Global Configuration_.

### Per-Artist Configuration *(optional)*

Within deemon, you can configure different settings for each individual artist 
(using the `config` command). This gives you the flexibility to disable alerts 
for certain artists or specify a certain release type, bitrate or download path.

<br>

## Global Configuration
This section outlines each setting available in the configuration file and their respective options.

---

### Global settings
These settings affect the general operation of deemon.

|Setting|Description|
|-|---|
|**check_update**<br><br><br>|This option allows you to specify how frequently (in days) to check for new updates to deemon. To disable checking for updates, change this to `0`.<br><br>|
|**debug_mode**<br>options: _true, false_<br><br>|This option will allow you to print extra debug messages in the logs or on screen if used with `--verbose`.<br><br>|
|**release_channel**<br>options: _stable, beta_<br><br><br>|When checking for updates (if enabled), this option allows you to choose what updates you are notified about. Most users will want to use _stable_. If you are interested in testing pre-release versions of deemon, you can set this to _beta_.<br><br>|
|**query_limit**<br>options: _number_<br><br><br>|This option allows you to specify how many results are displayed when using the `search` command or when prompted using the `monitor` command (see _prompt_duplicates_ and _prompt_no_matches_ below).<br><br>|
|**smart_search**<br>options: _true, false_<br><br><br>|This option allows you to skip the list of artist search results and proceed directly to the list of artist albums, provided there is only one exact match of the artists name (case insensitive).<br><br><br>|
|**rollback_view_limit**<br><br><br>|This option allows you to specify the maximum number of transactions to display using the `rollback` command<br><br>|
|**prompt_duplicates**<br>options: _true, false_<br><br><br><br>|When adding a new artist using the `monitor` command, deemon will choose the highest ranked artist in situations where two artists have identical names. Instead, you can set this option to `true` which will prompt you with choices including the latest release from each artist to help you better decide which is the artist you're looking for.<br><br>|
|**prompt_no_matches**<br>options: _true, false_<br><br><br>|When adding a new artist using the `monitor` command, if deemon does not find an **exact** match for the artist you're searching for, it will prompt you with a list of results returned from the Deezer API.<br><br>|
|**fast_api**<br>options: _true, false_<br><br>|In previous versions of deemon, this was referred to as the _experimental_api_ and has been the default API since version 2.1.<br><br>|
|**fast_api_threads**<br>options: _number_<br><br>|This sets the number of threads to spawn when accessing the API. The higher the number, the faster artist data is retrieved. However, setting this number too high may result in a temporary ban of your IP address. **It is recommended to keep this number below 50.**<br><br>|

---

### Exclusion settings
Exclusions can be setup to ignore releases matching a specific regular expression ("pattern") or by matching against specific keywords. You can test your exclusion settings by using the `test` command.

|Setting|Description|
|-|---|
|**enable_exclusions**<br>options: _true, false_<br><br>|This setting enables exclusion patterns and keywords (below) to filter out releases.<br><br><br>|
|**patterns**<br>options: _regex_<br><br>|Provide a list of regular expressions to filter out releases.<br><br><br>|
|**keywords**<br>options: _true, false_<br><br>|Provide a list of keywords to filter out releases (_remix, deluxe, bonus_).<br><br><br>|

---

### New Release settings
These settings affect what releases are filtered out by deemon. As of version 2.9, these settings are global only and cannot be configured in a profile nor per-artist configuration.

|Setting|Description|
|-|---|
|**release_max_age**<br><br><br><br><br><br><br><br>|This lets you control how far back to consider a new release 'new' from it's actual release date. This setting is helpful if you only run a `refresh` monthly or if there is a delay in Deezer adding a release to their catalogue. If you wish to get all releases regardless of when they were released, set this to _0_.<br><br>**Note:** Version 2.8.x and earlier relied on a separate toggle _by_release_date_ which has been deprecated in favor of setting _release_max_age_ to _0_.<br><br>|
|**include_unofficial**<br>options: _true, false_<br><br><br><br><br><br>|Each release result returned from the API includes a boolean value designating the release as either an official artist release or not. In many cases, this flag is incorrectly set resulting in some official releases not being detected.<br><br>**Warning:** If you are enabling this option on an existing database, you could potentially have hundreds or thousands of new releases detected.<br><br>|
|**include_compilations**<br>options: _true, false_<br><br><br><br><br>|If you want to include all compilation albums that your artists are featured on, you can enable this.<br><br>**Warning:** If you are enabling this option on an existing database, you could potentially have hundreds or thousands of new releases detected.<br><br>|
|**include_featured_in**<br>options: _true, false_<br><br><br><br><br><br>|Enabling this option will include every single release/track an artist is associated with. It is highly recommend to avoid using this but is included for testing purposes.<br><br>**Warning:** If you are enabling this option on an existing database, you could potentially have **_tens of thousands_** of new releases detected. Most users will NOT want this option enabled.<br><br>|

---

### Global settings
These settings can be overriden within deemon using _profiles_ or by specifying a _per-artist configuration_.

|Setting|Description|
|-|---|
|**bitrate**<br>options: _128, 320, FLAC_<br><br>|This option allows you to specify the bitrate used for downloads.<br><br><br>|
|**alerts**<br>options: _true, false_<br><br>|Enable or disable email notification alerts when new releases are present. You must also have your email settings configured (see _[SMTP Settings](#smtp-settings)_).<br><br>|
|**record_type**<br>options: all, album, ep, single<br><br><br>|This option allows you to specify what release types you wish to download upon release. Keep in mind, most EPs are labelled as albums in the Deezer API.<br><br>**Limitation:** Currently only one option at a time is allowed.<br><br>|
|**download_path**<br><br><br><br><br><br>|This option allows you to specify where downloads are saved. If no path is provided, downloads will be saved in the default directory specified by deemix.<br><br>**Windows users:** When providing a path, you **must** use double backslashes: `C:\\Music` or forward slashes: `C:/Music`.<br><br>|
|**email**<br><br><br>|This option allows you to specify the default email address to use when alerts are enabled and SMTP settings are defined.<br><br>|

---

### deemix settings
These settings are needed for deemon to interface with deemix which is a third party library that does the actual downloading.

|Setting|Description|
|-|---|
|**path**<br><br><br>|Specify the path to where your deemix configuration is stored. For most users, leave this blank. If you have moved the deemix configuration, you must specify that here.<br><br>|
|**arl**<br><br><br><br>|This is your authorization token required by `deemix` to authenticate your Deezer account. This is stored in a cookie named `arl` in your browser after logging in to Deezer.<br><br>|
|**check_account_status**<br>options: _true, false_<br><br><br><br>|This option allows you to force account verification before doing a refresh. If you have _bitrate_ set to FLAC and your account type is not HiFi, deemon will exit until you correct the issue (expired ARL or subscription). This option is useful for preventing low quality downloads due to an expired subscription.<br><br>|
|**halt_download_on_error**<br>options: _true, false_<br><br>|If enabled, deemon will exit if deemix reports any errors when downloading. This prevents releases from being logged in the database so that you can try again later.<br><br>|

---

### SMTP settings
These settings are needed for deemon to interface with deemix which is a third party library that does the actual downloading.

|Setting|Description|
|-|---|
|**server**<br><br>|Server address for your mail server<br><br>|
|**port**<br><br>|Port used to connect to your mail server (typically 587 or 465)<br><br>|
|**starttls**<br>options: _true, false_<br>|If your mail server requires STARTTLS, you can enable that here.<br>|
|**username**<br><br>|Username required to login to your mail server<br><br>|
|**password**<br><br>|Password used to authenticate your account with your mail server<br><br>|
|**from_addr**<br><br><br>|This is the email address your email is to be sent _from_ and typically must be a real address associated with your account on your mail server.<br><br>|

---

### Plex integration settings
deemon features support for refreshing your Plex library after a download operation is complete. Plex has the ability to automatically detect changes and rescan but if you're having issues with that, this should help.

|Setting|Description|
|-|---|
|**base_url**<br><br><br><br><br><br><br>|This is the URL to reach your Plex server including the port and protocol.<br><br>_Example_: http://192.168.0.2:32400<br><br>**Note:** You may need to use _https_ if your Plex setup is configured for secure connections.<br><br>|
|**ssl_verify**<br>options: _true, false_<br>|If you have Plex configured to require secure connections, but have not provided a custom certificate, keep this set to _false_ to avoid SSL certificate errors.<br><br>|
|**token**<br><br><br><br>|Authentication token required to connect to your Plex server<br><br>For instructions on how to find your token, [click here](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).<br><br>|
|**library**<br><br>|The name of your Plex library to be refreshed.<br><br>|