---
layout: default
title: config
parent: Commands
---

# config
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
The `config` command allows you to specify a per-artist configuration that overrides _global_ and _profile_ 
configurations for one specific artist.

If you wish to clear a particular setting for an artist, type 'none'. Providing no input leaves the setting unchanged.

```bash
user@localhost:~$ deemon config ARTIST
deemon Artist Configurator
:: Configuring 'ARTIST' (Artist ID: ...)

Bitrate [None]: 320
Record Type [None]: album
Alerts [None]: true
Download Path [None]:

:: Save these settings? [y|N] y

Artist 'ARTIST' has been updated!
```