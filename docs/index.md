---
layout: default
title: Home
nav_order: 1
description: "deemon is a monitoring utility for new artist releases that can provide email alerts and automate downloading via the deemix library"
permalink: /
---

# deemon Documentation
{: .fs-9 }

deemon is a monitoring utility for new artist releases that can provide email alerts and automate downloading via the deemix library
{: .fs-6 .fw-300 }

[Get started now](#getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 } [View it on GitHub](https://github.com/digitalec/deemon){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Getting started

### Dependencies

deemon depends on various python modules and libraries to perform all of its functions. The following dependencies are automatically installed when deemon is installed using the `pip` package manager

```
deezer-py deemix plexapi packaging requests click progressbar
```

### First use

The first time you run deemon, you'll need to start monitoring an artist. Monitoring an artist can be done simple by using the `monitor` command:

```bash
$ deemon monitor Artist
```

### Configure deemon

- [See configuration options]({{ site.baseurl }}{% link docs/configuration.md %})

---

## About the project

deemon is an open source project that came from the need to stay on top of new releases by some of my favorite artists

### License

deemon is distributed by a [GPL-3.0 license](https://github.com/digitalec/deemon/blob/main/LICENSE).
