---
layout: default
title: show
parent: Commands
---

# show
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
Using the `show` command, you can currently view information pertaining to artists and new releases.

## Show Artists
**Options**: `-a, --artists`

Show all currently monitored artists
```bash
$ deemon show --artists
ArtistA
ArtistB
```
Show using `-c, --csv`:
```bash
$ deemon show -ac
ArtistA, ArtistB
```

## Show Artist IDs
**Options**: `-i, --artist-ids`

Show all currently monitored artist IDs:
```bash
$ deemon show --artist-ids
1234
4567
```
Show using `-c, --csv`:
```bash
$ deemon show -ic
1234, 4567
```


## New Releases
Show all new releases in last N days
```bash
$ deemon show --new-releases 7
```
