---
layout: default
title: refresh
parent: Commands
---

# refresh
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
The `refresh` command is used to check for new releases, update the database and queue new releases with deemix for download. By default, running `refresh` will refresh the both artists and playlists for the active profile.

## Refresh
By executing the `refresh` command by itself, deemon will refresh the releases for all artists and playlists contained in your database.

> **Note:** For large databases, this can take several minutes to complete.

```bash
user@localhost:~$ deemon refresh
```

## Refreshing a single artist
The `refresh` command has the ability to refresh a single artist or your entire database. To refresh an artist, simply specify that artists name after the `refresh` command:

```bash
user@localhost:~$ deemon refresh Artist Name
```

## Refreshing a single playlist
The `refresh` command also has the ability to refresh a single playlist. To refresh a playlist, specify that playlists name after the `refresh` command:

```bash
user@localhost:~$ deemon refresh My Awesome Playlist
```

## Refreshing with downloads disabled
If you wish to run a refresh without downloading any releases automatically, you can specify `--skip-download`.

## Refresh to a specific date
The `refresh` command has a feature developed for resetting the database to a certain point in time called _time machine_. This makes rebuilding a music collection simple and can also ensure you have all releases released after a certain date.

Let's say for example you want to download all releases released on or after January 1, 2022 for your entire database. All you have to do is run _time machine_ with the date of the day prior:

```bash
user@localhost:~$ deemon refresh --time-machine 2021-12-31
```

This tells deemon to first clear any release from the database that is newer than _December 31, 2021_ and then will do a full refresh. Any releases found between _January 1, 2022_ and today's date will be queued for download.

In the event a release is found with a release date in the future, deemon will save this to the database and flag it is a _future release_. Once the release date of the _future release_ has come, that release will then be queued for download.