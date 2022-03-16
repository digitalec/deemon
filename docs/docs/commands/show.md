---
layout: default
title: show
parent: Commands
---

# show
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
Using the `show` command, you can currently view information pertaining to artists, playlists and new releases. You can also view artist and playlist data in CSV format and export that data to a CSV file.

## Viewing artists or playlists
To show a list of monitored artists:

```bash
$ deemon show artists
ArtistA
ArtistB
```

To show a list of monitored playlists:

```bash
$ deemon show playlists
Summer Hits Playlist
2022 Indie Folk
```

## CSV, filters and exporting data
The `show` command allows you to view and export more data pertaining to each artist other than just their names.

### Viewing the data in CSV format
First, we'll use the `-c` or `--csv` option to see all the data available:
```bash
$ deemon show artists --csv
name,id,bitrate,alerts,type,path
John Doe,1234,,,,
```

You can also toggle the header of the CSV output by passing `--hide-header` or `-H`:

```bash
$ deemon show artists -cH
John Doe,1234,,,,
```

### Using filters to customize the CSV output
Next, we can apply filters to view only certain pieces of this data. If you would like to generate a CSV file containing only the ID and artists' name, you can do so by using the `-f` or `--filter` option:
```bash
$ deemon show artists --csv --filter id,name
id,name
1234,John Doe
```

Notice how the data is presented in the order in which you specify the filters. Filters can also be used more than once if you find the need to do so:

```bash
$ deemon show artists -cf id,name,id
id,name,id
1234,John Doe,1234
```

### Exporting monitored artists
Another option for the `show artists` command is `-e` or `--export`. This allows you to export your artists to a CSV file. You can also combine this with `--hide-headers` and `--filter` to customize the data output to meet your needs.

```bash
$ deemon show artists --export artists.csv
CSV data has been saved to: artists.csv

$ cat artists.csv
name,id,bitrate,alerts,type,path
John Doe,1234,,,,
```

A common use case is backing up a list of all monitored artist IDs to a CSV file which you can then import into deemon if you ever want to rebuild your database:

```bash
$ deemon show artists -Hf id -e artists.csv
CSV data has been saved to: artists.csv

$ cat artists.csv
1234
```

Introduced in version 2.9 is a new alias option `-b` or `--backup`. This option does the exact same thing as the previous example but does so in a much more user-friendly and simple way:

```bash
$ deemon show artists --backup artists.csv
CSV data has been saved to: artists.csv

$ cat artists.csv
1234
```

## New releases
You can view a list of releases that have been detected in chronological order (newest to oldest). By default, `show releases` will display the last 7 days worth of releases. You can override this by specify a number like so:

```bash
$ deemon show releases 30
```

## Future releases
You may have seen `Pending future releases` displayed in the output of the `refresh` command. When deemon detects a release with a release date in the future, it is flagged and is stored in the database until the release date approaches.

If you'd like to view these future releases, you can use the `show` command:

```bash
$ deemon show releases --future
```