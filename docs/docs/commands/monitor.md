---
layout: default
title: monitor
parent: Commands
---

# monitor
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
Monitoring artists is the core feature of deemon. Using the `monitor` command, you can monitor artists by name, their Deezer ID or Deezer URL. Starting with version 1.1, you can now provide multiple values in CSV format.

## Monitor by Artist Name
This is the easiest way to monitor an artist but has some limitations. When using an artist name, deemon searches Deezer via an API call which returns the most likely result. In some situations you may find yourself monitoring the wrong artist. In this case, it would be best to [monitor the artist by ID](#monitor-by-artist-id).
```bash
$ deemon monitor My Awesome Band
```

## Monitor by Artist ID
**Options**: `-i, --artist-id`

The Artist ID is the number located in the URL after `/artist/` and can be used to monitor an artist directly. This is the most accurate way to monitor an artist because this number is unique.

If monitoring by artist name doesn't give you the correct artist or an artist has more than one artist profile, this method is guaranteed to give you this exact artist.

```bash
$ deemon monitor --artist-id 1234
```

## Monitor by URL
**Options**: `-u, --url`

Monitoring by URL was implemented with the intention of using it for integration with automation tools like Siri Shortcuts.

```bash
$ deemon monitor --url https://www.deezer.com/us/artist/1234
```

## Import artists from file or directory
**Options**: `-I, --import`

This method imports artist names or IDs from a file (CSV or Text) or a directory and stores them in the database.

_**Note**: As of version 1.3, this does not actively monitor a file or directory for changes. This strictly imports the artists._

**File Method:**
```bash
$ deemon monitor --import file.csv
```

**Directory Method:**
```bash
$ deemon monitor --import /home/user/Music
```

## Specify custom bitrate, record type and alerts
**Options**: `-b, --bitrate; -t, --record-type; -a, --alerts`
You can override the config.json and specify one-off settings for monitoring:

```bash
$ deemon monitor ArtistA --bitrate 9 --record-type album --alerts 0
```

_This will monitor `ArtistA` for new albums, download in FLAC without alerts._

## Stop Monitoring an Artist
**Options**: `-R, --remove`

If you no longer wish to monitor an artist, include the `--remove` flag with one of the above methods and they will be removed from the database.

```bash
$ deemon monitor --remove ArtistA
$ deemon monitor --remove --artist-id 1234
```

## Reset database
**Options**: `--reset`

To reset the database and remove all artists/playlists from monitoring:
```bash
$ deemon monitor --reset
** ALL ARTISTS AND PLAYLISTS WILL BE REMOVED! **
Type 'reset' to confirm: reset
Database has been reset

```

## Skip Refresh
**Options**: `-n, --no-refresh`

If you'd like to monitor an artist and wish to bypass refreshing the database afterwards, simply add `-n, --no-refresh`.
