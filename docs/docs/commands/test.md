---
layout: default
title: test
parent: Commands
---

# test
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
## SMTP settings test
To verify that your SMTP settings are correctly configured, you may use `test --email` to send a test email to yourself. If you don't receive the email, confirm your SMTP settings with your mail provider and check the logs for additional information.

---
## Exclusions test
If you have opted to use exclusion patterns or keywords to filter out releases, you may test those exclusions against any release URL to identify if that URL will be appropriately filtered out:

```
Artist: Various Artists
Album: Broken Bow (Remix)

Checking for the following patterns:
  1.  (?i)\bremix\b   >>   ** MATCH **

Checking for the following keywords:
  1.  remix   >>   ** MATCH **
  2.  deluxe   >>   NO MATCH
  3.  bonus   >>   NO MATCH
  4.  special   >>   NO MATCH
  5.  live   >>   NO MATCH

Result: This release would be excluded
```
