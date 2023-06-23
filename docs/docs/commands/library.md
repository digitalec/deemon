---
layout: default
title: library
parent: Commands
---

# library
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
**Warning: This feature is a working prototype and is provided as-is. It should work but it requires accurate local metadata when querying for track/album IDs.**

Starting in v2.18, deemon includes a library upgrade script to upgrade your existing collection from MP3 to FLAC by generating a file containing track/album IDs to be used with the `download` command.

## Generate Track IDs
To generate a file containing track IDs:

```bash
user@localhost:~$ deemon library upgrade /path/to/music/library
```

This will generate a file in the current working directory called `library_upgrade_ids.txt`.

## Generate Album IDs
To generate a file containing album IDs:

```bash
user@localhost:~$ deemon library upgrade -A /path/to/music/library
```

## Specify output path of ID file

```bash
user@localhost:~$ deemon library upgrade -O /path/to/save /path/to/music/library
```

## Obey exclusions set in config.json
If you'd like to obey the exclusions defined in your config.json file, add `-E` or `--allow-exclusions`.

```bash
user@localhost:~$ deemon library upgrade -E /path/to/music/library
```

## Using library_upgrade_ids.txt
To process this file for downloading of the tracks/albums, use one of the following commands depending on which type of file you have generated:

Track IDs:
```bash
user@localhost:~$ deemon download --track-file library_upgrade_ids.txt
```

Album IDs:
```bash
user@localhost:~$ deemon download --album-file library_upgrade_ids.txt
```