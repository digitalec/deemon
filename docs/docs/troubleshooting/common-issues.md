---
layout: default
title: Common Issues
parent: Troubleshooting
---

# Common Issues
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
## Requests

## Log file in use
If you're using _deemix-pyweb_ on the same system as deemon, you may run into an issue where deemon cannot call deemix because a log file is already in use.

If this happens, it is recommended to make a copy of the deemix config folder. This will allow deemix to run and create a separate log file in this new directory. You **must** set the _deemix_config_ setting in deemon's _config.json_ to point to this new directory.

## Error: ARL is invalid, expired or missing
This error will appear when deemon cannot locate your _.arl_ to send to deemix. Make sure you have run the command line application "deemix" at least once prior to using deemon. Keep in mind, _deemix-pyweb_ and _deemix_ are not the same thing!