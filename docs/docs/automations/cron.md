---
layout: default
title: cron (Linux/macOS)
parent: Automations
nav_order: 1
---

# cron
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
A cron job is the ideal way to run deemon in regular intervals to check for new releases or to "watch" a directory.

## Watch Directory

You can create a cron job that periodically imports a directory to make sure any new artists are automatically monitored. This example scans and imports all artist subdirectories in _/path/to/music_ every day at midnight:

```bash
$ crontab -l
0 0 * * * deemon import /path/to/music
```

## Check for New Releases

This example checks for new releases every day at 06:00:

```bash
$ crontab -l
0 6 * * * deemon refresh
```
