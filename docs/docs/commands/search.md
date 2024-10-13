---
layout: default
title: search
parent: Commands
---

# deemon Interactive Search Client (dISC)
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
The `search` command is an interactive client to search for artists and download albums or setup monitoring.

To open the search client:

```bash
$ deemon search
```

You will then be prompted for an artist to search for:
```bash
deemon Interactive Search Client

:: Enter an artist to search for:
```

You can also save yourself a step and include your query as an argument to the search command:

```bash
$ deemon search ArtistA 
```

## Search Results
When searching for an artist, you'll be presented with a list of results. If you have `smart_search` enabled, you will be taken to the releases menu provided that there was only one exact match.

In the event more than one artist is found with the exact same name, you'll be presented with some data regarding that artist to help you determine the one you're looking for:

```bash
Search results for artist: John Doe
    1. John Doe
       - Latest release: One Hit Wonder (1996)
       - Artist ID: 1234
       - Total releases: 1
    2. John Doe
       - Latest release: Broken (2020)
       - Artist ID: 3210329
       - Total releases: 14

(b) Back
** Duplicate artists found **
:: Please choose an option or type 'exit': 
```

<small><center>Search results showing a duplicate match</center></small><br>

Judging by the results, it's possible that both artists are the same artist but for some reason have two separate artist profiles. It's also possible that they are unrelated and both artists happen to have the same name. You can then (hopefully) tell them apart based on their _Latest release_ and also by their _Total releases_. The _Artist ID_ is provided for reference so you can visit that specific artist in a browser if you need to.

## Navigation

```bash
Discography for artist: John Doe
Filter by: All | Sort by: Year (desc)

   1. (2020) Broken
   2. (2018) Greatest Hits

Filters: (*) All  (a) Albums  (e) EP  (s) Singles - (E) Explicit (r) Reset
   Sort: (y) Year Desc  (Y) Year Asc  (t) Title Desc  (T) Title Asc
   Mode: (S) Toggle Select

(b) Back  (d) Download Queue  (Q) Show Queue  (f) Queue Filtered  (m) Stop Monitoring
:: Please choose an option or type 'exit':
```

<small><center>The interface when viewing an artist's discography.</center></small><br>

At the top of the screen is information related to the menu you are currently on. In the example above you can see that you are looking at the _Discography_ for the artist _John Doe_.

At the bottom of the screen you see four rows: Filters, Sort, Mode and Actions.

### Filters
Here you can filter albums by type (albums, EP and singles), show only explicit releases and reset filters back to their default view.

As of v2.22, you can now filter by date using `>=`, `<=` or `=` followed by the four digit year. For example, to find all releases between (and including) 2000 and 2003:

Released in year 2000 or later:
```bash
:: [SELECT] Please choose an option or type 'exit': >=2000
```

Released in year 2003 or prior:
```bash
:: [SELECT] Please choose an option or type 'exit': <=2003
```

You'll notice the header has updated to reflect the filter:
```bash
Filter: All | Sort: Release Date (desc) | Year: 2000 - 2003
```

### Sorting
You can sort the results by release year and title, both ascending and descending.

### Modes
There are two different _Modes_ available when it comes to selecting releases.

_Regular_ mode is the default mode which displays a number to the left of each menu item.

_Select_ mode allows you to select an album or track to add to the queue and is identified by two brackets: `[ ]` for unselected and `[*]` for selected. When selecting items, the prompt will change to let you know you are in _Select_ mode and how many items are in the queue:

```bash
:: [SELECT] Please choose an option or type 'exit' (1 Queued):
```

### Actions

The _Actions_ bar is a group of actions you can perform while in the current view. Below is a list of all available actions throughout the dISC interface. You can only use an option if it is available in the _Actions_ bar.

|Key|Name|Description|
|-|--|---|
|b|Back|Go back to the previous screen|
|d|Download Queue|Download items currently in queue|
|Q|Show Queue|Show all items presently in the queue|
|c|Clear Queue|Clear all items from the queue|
|f|Queue Filtered|Queue all items currently visible on the screen|
|m|Start/Stop Monitoring|Toggle monitoring status of an artist|
