---
layout: default
title: Import
parent: Commands
---

# Import
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
Starting with version 1.0, artists are no longer read from a file or directory during a `refresh`. Artists are imported into the database once (either through the `import` or `monitor` command) eliminating the need to pass a list of artists each time deemon is run.

## Text File
To import a list of artists via a text file, each line must contain only one artist. Each artist will be imported into the database and configured with the settings in your config.json file.

<small>**Example - artists.txt**</small>
```
My Band
My Friend's Band
Another Band
```


```bash
$ deemon import artists.txt
```

## Directory
Similarly to importing artists via a text file, deemon can read a directory listing that contains artist subdirectories.

<small>**Example - /home/user/music**</small>
```
$ ls -1
My Band
My Friend's Band
Another Band
```


```bash
$ deemon import /home/user/music
```
