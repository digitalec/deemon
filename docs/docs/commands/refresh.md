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
The `refresh` command is used to check for new releases, update the database and queue new releases with deemix:

```bash
$ deemon refresh
```

## Options
`-s, --skip-download` option allows you to refresh the database without downloading
`-t, --time-machine YYYY-MM-DD` option allows you to refresh as if it were a certain date in time

## Time Machine
Starting in v1.2, you can now specify a date in time to refresh your database on:

**Example:** First refresh records all releases that were released up to January 1, 2021. The second refresh will treat all releases after January 1, 2021 as new and will download and send a new release email (depending on your configuration).
```bash
$ deemon refresh --time-machine 2021-01-01
$ deemon refresh
```
