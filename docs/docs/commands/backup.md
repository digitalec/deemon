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
A backup can be created by using the `backup` command:

```bash
user@localhost:~$ deemon backup --include-logs
Backed up to /home/user/.config/deemon/backups/20210603-233151.tar
```

**Warning: ** Do **NOT** send your backup to anyone unless you have personally removed all sensitive data from your configuration such as email addresses, SMTP server settings and your ARL.

## Restore a Backup
To restore from an existing backup, use `backup --restore` to be presented with valid backups to restore from:

```bash
user@localhost:~$ deemon backup --restore
deemon Backup Manager

1. Sep 23, 2021 @ 1:32:05 AM (ver 2.0)

Select a backup to restore: 
```

**Note: ** You cannot restore from a backup that is newer than the version of deemon you are presently running. For example, if you create a backup while using deemon 2.9 you cannot restore it on version 2.8. However, you can restore manually by extracting the tar file and replacing the files as necessary. This is to prevent users from using an incompatible configuration or database versions.