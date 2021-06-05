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
Monitoring artists is the core feature of deemon. Using the `monitor` command, you can monitor artists by name, their Deezer ID or Deezer URL.

## Monitor by Artist Name
This is the easiest way to monitor an artist but has some limitations. When using an artist name, deemon searches Deezer via an API call which returns the most likely result. In some situations you may find yourself monitoring the wrong artist. In this case, it would be best to [monitor the artist by ID](#monitor-by-artist-id).
```bash
$ deemon monitor My Awesome Band
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

## Stop Monitoring an Artist
If you no longer wish to monitor an artist, include the `--remove` flag with one of the above methods and they will be removed from the database.

```bash
$ deemon monitor --remove ...
```
