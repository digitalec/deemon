---
layout: default
title: Siri Shortcuts (iOS)
parent: Automations
---

# Siri Shortcuts
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

* TOC
{:toc}

---
Siri Shortcuts can be used to run commands over SSH allowing you to integrate quick-and-easy ways to monitor or download from your iPhone. This example shows you how to monitor an artist by "sharing" the webpage to the shortcut.

## Monitor URL via Share Sheet

Using this Shortcut, you can simply share a webpage to the shortcut which will connect via SSH and run the command for you.

### Getting Started

Open the Shortcuts app and create a new shortcut. Press the menu icon "..." in the upper right corner and give your shortcut a name. Make sure _Show in Share Sheet_ is also toggled on and _Share Sheet Types_ is set to _URLs_.

### Building the Shortcut

1. Create the first action by searching for _If_. Set the input to "Shortcut Input" and condition to "has any value".

2. Between _If_ and _Otherwise_, add the _Run script over SSH_ action.

3. Fill in your server settings. If you're using SSH keys, one will be generated and you'll need to copy this to your _~/.ssh/authorized_keys_ file before you can connect.

4. Set the _Input_ to _Shortcut Input_ if its not already. Below this, the _script_ will be `deemon monitor --url ` followed by the _Shortcut Input_ variable (_make sure there is a space after_ `--url`).

5. At this point, go ahead and find an artist you wish to monitor for new releases on Deezer and then share the page to your newly create Shortcut. This should automatically log in and run the `monitor` command. You can verify this was successful by checking the log file in the [deemon config directory](/docs/configuration#configuration-file).