---
layout: default
title: Upgrading from 0.4.x or earlier
nav_order: 1
---

# Upgrading
{: .no_toc }

Starting with version 1.0, deemon now uses a new database called `deemon.db`. This is located in the same directory as the legacy version, `releases.db`. The process outlined below is entirely optional but recommended to make sure no releases are missed since the last time you ran deemon.

## Perform refresh on 0.4.x

To verify your releases are up-to-date, run deemon as you normally would to refresh your database and grab any new releases:

<small>example - deemon 0.4.x</small>
```bash
$ deemon -a artists.txt
```


## Upgrade via pip

Once this is completed, you can perform the upgrade:

```bash
$ pip install --upgrade deemon
```

To generate the default config.json and verify you have the latest release, run:

```bash
$ deemon --version
deemon 1.0
```

## Configure prior to first use

By default, deemon is ready to go without any configuration changes. However, to get full use of deemon and it's features, it is recommended to take a look at the [configuration](/docs/configuration) page.

## Importing your artists into version 1.0

Using the file (or directory) you used with the previous deemon version, you can now import your list of artists into the deemon database:

```
$ deemon import artists.txt
Importing 25 artist(s), please wait...
[=====================================================] 100%

Refreshing artists, this may take some time...
[=====================================================] 100%
```

## Checking for new releases

One of the advantages of version 1.0 is how much easier it is to use. All you have to do to check for new releases is:

```bash
$ deemon refresh
Refreshing artists, this may take some time...
[=====================================================] 100%
```

That's it!