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

## Monitored Artists
Show all currently monitored artists
```bash
$ deemon show --artists
```

Optionally, you can add `-c, --csv` to output the list into CSV format which can be piped to another application or file.

## New Releases
Show all new releases in last N days
```bash
$ deemon show --new-releases 7
```
