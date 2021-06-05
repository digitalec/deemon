---
layout: default
title: backup
parent: Commands
---

# backup
{: .no_toc }

---

Introduced in version 1.0, you can now make backups of your deemon installation including your _config.json_, _deemon.db_ and (optionally) the _logs_ directory.

```bash
$ deemon backup --include-logs
Backed up to /home/user/.config/deemon/backups/20210603-233151.tar
```

To restore from a backup, delete the contents of your `deemon` directory and extract the tar file inside.
