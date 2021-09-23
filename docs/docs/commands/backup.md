---
layout: default
title: backup
parent: Commands
---

# backup
{: .no_toc }

---

Introduced in version 1.0, you can now make backups of your deemon installation including your _config.json_, 
_deemon.db_ and (optionally) the _logs_ directory.

## Creating a Backup
A backup can be created by issuing the `backup` command.

```bash
user@localhost:~$ deemon backup --include-logs
Backed up to /home/user/.config/deemon/backups/20210603-233151.tar
```

## Restore a Backup
To restore from an existing backup, use `backup --restore` to be presented with valid backups to restore from:

```bash
user@localhost:~$ deemon backup --restore                                                                                                 ✔  2m 43s  
deemon Backup Manager

1. Sep 23, 2021 @ 1:32:05 AM (ver 2.0)

Select a backup to restore: 
```