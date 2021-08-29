---
layout: default
title: download
parent: Commands
---

# download
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
deemon includes a command line interface to the deemix library allowing you to download by artist, artist ID, album ID or URL.



## By Artist
Artist names can be entered one at a time or in CSV format as shown below:
```bash
$ deemon download ArtistA, ArtistB, ArtistC
```

## By Artist ID
**Options**: `-i, --artist-id`

```bash
$ deemon download --artist-id 1234
```

You can download multiple artist IDs at once:
```bash
$ deemon download -i 1234 -i 4567
```

## By Album ID
**Options**: `-A, --album-id`
```bash
$ deemon download --album-id 1234
```

You can download multiple album IDs at once:
```bash
$ deemon download -A 1234 -A 4567
```

## By URL
**Options**: `-u, --url`

Downloading by URL was implemented with the intention of using it for integration with automation tools like Siri Shortcuts.

```bash
$ deemon download --url https://www.deezer.com/us/artist/1234
```

You can download multiple URLs at once:
```bash
$ deemon download -u https://www.deezer.com/us/artist/1234 -u https://www.deezer.com/us/artist/4567
```

## By File
**Options**: `-f, --file`

You can queue up a batch of artists from CSV or by adding one artist per line to a text file:

```bash
$ deemon download --file artists.txt
```

## Specify custom bitrate and record type
You can override the config.json and specify one-off settings for downloads such as bitrate and record type:

```bash
## Download all album releases in FLAC format by My Band

$ deemon download "My Band" --bitrate 9 --record-type album
```
