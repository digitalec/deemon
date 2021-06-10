---
layout: default
title: Configuration
nav_order: 2
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

## Configuration File
Depending on your operating system, your config.json file will be located in one of the following locations:

| OS        | Path       |
|:--------------|:------------------|
| Linux | /home/_user_/.config/deemon |
| macOS | /User/_user_/Library/Application Support/deemon |
| Windows | %appdata%\deemon |

<small>**config.json - v1.0 default**</small>
```json
{
    "plex_baseurl": "",
    "plex_token": "",
    "plex_library": "",
    "download_path": "",
    "deemix_path": "",
    "release_by_date": 1,
    "release_max_days": 90,
    "bitrate": "320",
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

## Plex

deemon can initiate a refresh of a given Plex library to ensure Plex sees new music as soon as its available. Plex does have ways of monitoring folders for changes but sometimes this doesn't always work or may be delayed.

To use this feature, you'll need to provide the following configuration values in your config.json:

| option        | description       |
|:--------------|:------------------|
| plex_baseurl       | Address to your Plex server - _http://127.0.0.1:32400_ |
| plex_token | Authentication token [(instructions)](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) |
| plex_library   | Name of the Plex library to refresh |

## Email Notifications
When deemon performs a refresh and finds a new release, you can choose to receive email notifications containing a list of all releases that were found. This feature can be enabled by setting the _alerts_ parameter to _1_.

| option        | description       | allowed values |
|:--------------|:------------------|:---------------|
| alerts | enable or disable email notifications | 0 [disable] or 1 [enable] |
| smtp_server | outgoing mail server |
| smtp_port | outgoing mail server port |
| smtp_user   | username of outgoing mail server |
| smtp_pass | password for outgoing mail account |
| smtp_sender | "from" address |
| smtp_recipient | "to" address |


## Release Handling

### Quality & Downloads
Specify settings that override default deemix values

| option        | description       | allowed values |
|:--------------|:------------------|:-------|
| bitrate       | choose between MP3 or FLAC | 128, 320, FLAC |
| download_path | path to download music | deemix default path |
| deemix_path   | path to deemix config directory | deemix default path |

### Release Options
The following options pertain to handling releases. By default, deemon checks each monitored artist for new releases with release dates no older than 90 days. This number can be adjusted by changing the value of _release_max_days_.

If _release_by_date_ is set to 0 (disabled), any new release will be considered new even if its an older release recently added to Deezer's library.

You may also wish to monitor only for new full-length albums which can be set using the _record_type_ parameter. Keep in mind, most EPs are labeled as albums so if you're missing releases, avoid using the "ep" designation.

| option        | description       | allowed values |
|:--------------|:------------------|:-------|
| release_by_date | verify release date is newer than release_max_days | 0 [disable] or 1 [enable] |
| release_max_days | max amount of days to consider new release | # days (_default: 90_) |
| record_type | monitor only for specific record types | all, album, ep, single |

