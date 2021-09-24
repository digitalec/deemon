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
The `refresh` command is used to check for new releases, update the database and queue new releases with deemix for 
download. By default, running `refresh` will refresh the both artists and playlists for the active profile.

## Performing a dry run
You can perform a refresh with the `--dry-run` option to simulate a refresh without comitting any changes to the 
database. This option also automatically sets `--skip-download` to `True`.

## Refreshing with downloads disabled
If you wish to run a refresh without downloading any releases automatically, you can specify `--skip-download`.

## Time Machine
Time machine is a feature developed for initializing the database at a certain point in time. The idea is that you add 
all the artists you wish to monitor using the `--no-refresh` option and then you can run a refresh with the 
`--time-machine YYYY-MM-DD` option which performs the initial refresh for all artists on that given date. This makes 
rebuilding a music collection easy and can also ensure you have all releases since a certain point in time.

```bash
# Monitor the artists first, on a clean database.
user@localhost:~$ deemon monitor ArtistA, ArtistB, ArtistC, ... --no-refresh

# Now, activate time machine; grabbing all releases from January 1, 2021
user@localhost:~$ deemon refresh --time-machine 2021-01-01
```