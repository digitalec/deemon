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

You can monitor multiple artists at once by comma separating the artist names.

```bash
user@localhost:~$ deemon monitor ArtistA, ArtistB, ArtistC
```

## Monitor by Artist ID
The Artist ID is the number located in the URL after `/artist/` and can be used to monitor an artist directly. This is the most accurate way to monitor an artist because this number is unique.

If monitoring by artist name doesn't give you the correct artist or an artist has more than one artist profile, this method is guaranteed to give you this exact artist.

```bash
$ deemon monitor --artist-id 1234
```

## Monitor by URL

Monitoring by URL was implemented with the intention of using it for integration with automation tools like Siri Shortcuts.

```bash
$ deemon monitor --url https://www.deezer.com/us/artist/1234
```
## Monitor by Playlist

Deemon will monitor the playlist URL, and will download any new additions to the playlist.

```bash
$ deemon monitor --playlist https://www.deezer.com/en/playlist/1234
```

## Monitor Playlist including Playlist Artists
If you'd also like to setup monitoring for artists included in your playlist, you can add `--include-artists`:

```bash
$ deemon monitor --playlist https://www.deezer.com/en/playlist/1234 --include-artists
```

## Import artists from file or directory

This method imports artist names or IDs from a file (CSV or Text) or a directory and stores them in the database.

>**Note**: As of version 1.3, this does not actively monitor a file or directory for changes. This strictly imports the artists.

**File Method:**
```bash
$ deemon monitor --import file.csv
```

**Directory Method:**
```bash
$ deemon monitor --import /home/user/Music
```

## Specify custom bitrate, record type and alerts
By default, deemon uses the settings configured in the `config.json` configuration file for all operations. This can be overridden at any time by using the available options such as `--bitrate`, `--record-type` and `--alerts`.

```bash
$ deemon monitor ArtistA --bitrate FLAC
```

## Monitor and download existing releases
When setting up an artist (or artists) for monitoring, you can use the `-D` or `--download` flag to also download all releases matching the configured `record_type`.

## Stop Monitoring an Artist

If you no longer wish to monitor an artist, include the `--remove` flag with one of the above methods and they will be removed from the database.

```bash
$ deemon monitor --remove ArtistA
$ deemon monitor --remove --artist-id 1234
```

## Stop Monitoring a Playlist

If you no longer wish to monitor an playlist, include the `--remove --playlist` flags along with the playlist URL.

```bash
$ deemon monitor --remove --playlist https://www.deezer.com/en/playlist/1234
```

## Reset database

To reset the database and remove all artists/playlists from monitoring:
```bash
$ deemon monitor --reset
** ALL ARTISTS AND PLAYLISTS WILL BE REMOVED! **
Type 'reset' to confirm: reset
Database has been reset

```

## Skip Refresh

If you'd like to monitor an artist and wish to bypass refreshing the database afterwards, simply use `--no-refresh`.
