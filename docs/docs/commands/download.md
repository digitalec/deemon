---
layout: default
title: download
parent: Commands
---

# download
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
deemon includes a command line interface to the deemix library allowing you to download directly by artist name, 
artist ID, album ID or URL.

The `download` command inherits all global settings configured in `config.json` such as bitrate and record type. These settings can be overriden using options available with the `download` command.

The `download` command is fairly straightforward and usage information including options can be found by running `deemon download --help`. Below are a few common usages of the `download` command.

### Download by artist name
To download by artist name, simply run the `download` command followed by the artist's name:

```bash
user@localhost:~$ deemon download John Doe
```

### Download by artist ID
To download by the artist's ID:

```bash
user@localhost:~$ deemon download --artist-id 100
```

### Download by URL
In the below example, you can download a specific URL (artist, album, track or playlist):

```bash
user@localhost:~$ deemon download --url https://...
```

### Download all monitored artists
If you'd like to download all releases by all artists currently being monitored, you can use the `--monitored` option to do so:

```bash
user@localhost:~$ deemon download --monitored
```

### Download a date range
Introduced in version 2.5, you can now specify a date range when downloading releases.

To download releases by all monitored artists between January 1, 2022 and January 31, 2022:

```bash
user@localhost:~$ deemon download --monitored --after 2021-12-13 --before 2022-02-01
```