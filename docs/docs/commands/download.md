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

## Usage
To view help info and usage information:

```bash
$ deemon download -h
```

## Example Usage

### Artist Name
In the below example, you can download all _album_ releases, released on or after January 1, 2021 from artist 'Artist'. 

```bash
user@localhost:~$ deemon download Artist -f 2021-01-01 -t album
```

### URL
In the below example, you can download a specific URL (artist, album, track or playlist):

```bash
user@localhost:~$ deemon download -u https://...
```