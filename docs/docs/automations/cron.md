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
A cron job is the ideal way to run deemon in regular intervals to check for new releases:

## Check for New Releases

This example checks for new releases every day at 06:00:

```bash
$ crontab -l
0 6 * * * /home/user/.local/bin/deemon refresh
```
