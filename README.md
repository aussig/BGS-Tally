![BGS-Tally Logo](https://repository-images.githubusercontent.com/400106152/2666ea20-1f4d-4dcb-9ece-686c53a78910)

# BGS-Tally

[![CodeQL](https://github.com/aussig/BGS-Tally/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/aussig/BGS-Tally/actions/workflows/codeql-analysis.yml)
[![Crowdin](https://badges.crowdin.net/bgs-tally/localized.svg)](https://crowdin.com/project/bgs-tally)
[![GitHub Latest Version](https://img.shields.io/github/v/release/aussig/BGS-Tally)](https://github.com/aussig/BGS-Tally/releases/latest)
[![Github All Releases](https://img.shields.io/github/downloads/aussig/BGS-Tally/total.svg)](https://github.com/aussig/BGS-Tally/releases/latest)
[![Discord](https://img.shields.io/discord/698438769358929940?label=Discord&color=%2350007f)](https://discord.gg/YDNVtjPnnm)

A tool to track and report your Background Simulation (BGS) and Thargoid War (TW) activity in Elite Dangerous, implemented as an [EDMC](https://github.com/EDCD/EDMarketConnector) plugin. BGS-Tally counts all the BGS / TW work you do for any faction, in any system.

Based on BGS-Tally v2.0 by tezw21

As well as all the BGS tracking from Tez's original version, this modified version includes:

* Automatic on-foot Conflict Zone tracking (with settlement names)
* Automatic in-space Conflict Zone tracking
* TW tracking
* Logging of interactions with other CMDRs, with automatic Inara lookup for CMDR and Squadron
* Fleet Carrier materials tracking
* Fleet Carrier jump tracking
* Discord-ready information - quick Copy to Clipboard for the Discord text as well as posting directly to Discord
* An API to send data to other web applications.


# Initial Installation and Use

Full instructions for **installation and use are [here in the wiki &rarr;](https://github.com/aussig/BGS-Tally/wiki)**.


# Updating from a Previous Version

Since v3, upgrading is fully automatic. However, if you need to do a manual upgrade for some reason, **full instructions are [here in the wiki &rarr;](https://github.com/aussig/BGS-Tally/wiki/Upgrade)**.


# Discord Integration

The plugin generates Discord-ready text for copying-and-pasting manually into Discord and also supports direct posting into a Discord server or servers of your choice using webhooks. You will need to create webhook(s) on your Discord server first - **instructions for setting up webhooks within Discord are [here in the wiki &rarr;](https://github.com/aussig/BGS-Tally/wiki/Discord-Server-Setup)**.


# What is Tracked

The plugin includes both automatic and manual tracking of BGS and TW activity data.

* For a basic summary of what is tracked, see the **[Home Page of the wiki &rarr;](https://github.com/aussig/BGS-Tally/wiki#it-tracks-bgs-activity)**.
* For more detail, see the **[Activity Window section in the wiki &rarr;](https://github.com/aussig/BGS-Tally/wiki/Use#activity-window)**.


# Your Personal Activity and Privacy

If you're concerned about the privacy of your BGS activity, note that this plugin **does not send your data anywhere, unless you specifically choose to by configuring the Discord Integration or API Integration**.

## Local Files and Folders

It writes to the following locations, both in the `BGS-Tally` folder:

1. `activitydata\` - This folder contains all your BGS activity, organised in one file per tick.
2. `otherdata\` - This folder contains other data collected by BGS-Tally, including your currently active list of missions and the CMDRs you have targeted.

All of these files use the JSON format, so can be easily viewed in a text editor or JSON viewer.

(N.B. Older versions of BGS-Tally wrote to `Today Data.txt`, `Yesterday Data.txt` and `MissionLog.txt` in your `BGS-Tally` folder. If you run BGS-Tally v2.0.0 or later, these files are automatically converted to the new formats inside `activitydata\` and `otherdata\`).

## Network Connections

The plugin makes the following network connections:

1. To [CMDR Zoy's Tick Detector](http://tick.infomancer.uk/galtick.json) to grab the date and time of the lastest tick.
2. To [GitHub](https://api.github.com/repos/aussig/BGS-Tally/releases/latest) to check the version of the plugin to see whether there is a newer version available.
3. To [Inara](https://inara.cz/elite/) to anonymously check for available information on targeted CMDRs.
4. **Only if configured by you** to a specific Discord webhook on a Discord server of your choice, and only when you explicitly click the _Post to Discord_ button.
5. **Only if configured by you** to a specific web application of your choice to send your BGS / TW data for aggregation and analysis, via an API. You have control over whether you approve the initial connection, and can choose to terminate the connection at any time.


# Troubleshooting

If you are having problems with BGS-Tally, check out the **[Troubleshooting page &rarr;](https://github.com/aussig/BGS-Tally/wiki/Troubleshooting)**. If those troubleshooting solutions don't work, feel free to contact me in the `#support` channel on the [BGS-Tally Discord server](https://discord.gg/YDNVtjPnnm).


# Thank You

And finally, a huge thank you to:

* CMDR Tez, who wrote the original version of BGS-Tally - this simply wouldn't exist without his work.

* All the code contributors to this version - listed [here on Github](https://github.com/aussig/BGS-Tally/graphs/contributors).
* All the CMDRs who have provided their input, bug reports, feedback and ideas.
* All the translators who have given their time and effort:
    * French - CMDR Dopeilien and CMDR ThArGos
    * German - CMDR Ryan Murdoc
    * Hungarian - CMDR Lazy Creature and CMDR xtl
    * Italian - CMDR FrostBit / [@GLWine](https://github.com/GLWine)
    * Portuguese (Portugal) - CMDR Holy Nothing
    * Portuguese (Brazil) - CMDR FelaKuti
    * Russian - CMDR YAD and CMDR KuzSan
    * Serbian (Latin) - CMDR Markovic Vladimir
    * Spanish - CMDR HaLfY47
    * Turkish - CMDR Yu-gen
