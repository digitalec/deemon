---
layout: default
title: profile
parent: Commands
---

# profile
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
Profiles are a new feature of deemon and give you the ability to apply a set of configuration options to a completely 
separate set of monitored artists. Profiles were developed with the intention of keeping up-to-date on multiple, 
separate music libraries.

The default profile cannot be deleted but can be renamed and modified. To unset a setting, type "none" when prompted.

## Viewing an Existing Profile
You can view an existing profile and it's configuration by running the below command:

```bash
user@localhost:~$ deemon profile default
deemon Profile Editor
:: Showing profile 'default' (Profile ID: 1)

Name       Email                Alerts   Bitrate  Type     Plex Base URL       Plex Token     Plex Library         Download Path
default 
```

You can also view all existing profiles:
```bash
user@localhost:~$ deemon profile                                                                                                                                                        ✔ 
deemon Profile Editor
:: Showing all profiles

Name       Email                Alerts   Bitrate    Type     Plex Base URL          Plex Token         Plex Library         Download Path
default                                                                                                                                                                

Soundtracks                       0        320      album                                                                    /music/soundtracks  

Favorites                         1        FLAC     all                                                                      /music/favorites    
```

## Managing Profiles
You can add, edit and delete profiles using the following syntax:
```bash
deemon profile --add NAME

deemon profile --edit NAME

deemon profile --delete NAME
```
