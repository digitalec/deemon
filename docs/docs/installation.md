---
layout: default
title: Installation
nav_order: 2
---

# Installation
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Step 1 - Required Dependencies

In order to install and run deemon, you'll need to have at least Python 3.6 or higher installed along with the `pip` package manager.

Please refer to [python.org](https://www.python.org/downloads/) for more information.

### Step 2 - Installing deemon
Once you have at least Python 3.6 installed, go ahead and install deemon using 
`pip`. On some distributions, the `pip` command is for Python2. In this case, 
substitute `pip` for `pip3` in the commands below.

**Windows users**: These commands should be typed in a Command Prompt, Windows Terminal or Powershell window.

```bash
# Latest stable release
$ pip install deemon

# Latest release (including pre-release/beta)
$ pip install --pre deemon
```

At this point, pip will download deemon and any other modules required to allow 
deemon to function. Once it's complete, use the following command to make sure 
deemon is installed:

```bash
$ deemon -V
deemon 2.19.2
```

## Configuration & First Use

Congrats! If you've made it this far, you have successfully installed deemon. 
There are a few things you should configure before using deemon. Head on over 
to the [configuration](configuration.md) page to learn more.