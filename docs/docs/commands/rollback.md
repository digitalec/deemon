---
layout: default
title: rollback
parent: Commands
---

# reset
{: .no_toc }

---

The `rollback` command allows you to rollback the last N transactions or a specific transaction. A _transaction_ is 
created anytime an artist is monitored or a refresh finds new releases. This does not delete any downloaded files but 
can be useful in the event a download failed and you want to quickly re-download those releases.

## Rollback by last _N_ transactions
```bash
user@localhost:~$ deemon rollback 2                                                                                                       ✔  2m 22s  
Rolled back the last 2 transaction(s).
```

## Rollback a specific transaction
By default, deemon shows only the last 10 transactions. To change this, edit _rollback_view_limit_ in your config.json 
file to increase or lower this amount.

```bash
user@localhost:~$ deemon rollback --view
1. 10:00 AM - Added Ludwig van Beethoven and 389 releases
2. Yesterday, 8:22 PM - Added Mozart and 31 releases

Select specific refresh to rollback (or Enter to exit):
```