---
layout: default
title: Multi-User Support
nav_order: 2
---

# Multi-User Support
{: .no_toc }


Starting with version 2.0, deemon now supports multi-user setups. Users are managed using the `config users` command.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Configuration
deemon consists of a global config (`config.json`) and a user config (stored in the database). When deemon first starts,
the global config is initially loaded and the default user settings loaded on top. Any settings not configured in the
individual user settings fallback to the global config. This provides the ability to share common settings between users.
To specify a user to run deemon as, simply add `-U username` before any other command like so:

```bash
$ deemon -U guest refresh
```

## Adding Users
New users can be added using the following:

```bash
$ deemon config users add <username>
```

## Deleting Users
To delete a user, use the following:

```bash
$ deemon config users delete <username>
```

## Modifying Users
By default, deemon runs as user ID 1 which is the default user. You can enter the configurator to change any aspect of 
the user profile using the below command. The default user profile cannot be deleted.

```bash
$ deemon config users edit default
```

## Multi-Library support
Users are essentially nothing more than configuration profiles and can be used to simply monitor separate music libraries.
By configuring the Name, Plex Library and Download Path, deemon can be setup to monitor separate libraries while sharing
the global config settings such as the Plex Base URL and Token.