# Change Log

## vx.x.x - xxxx-xx-xx

### New Features:

* Localisation. The plugin is now translated into French, German, Italian, Portuguese (Portugal), Portuguese (Brazil), Russian, Spanish and Turkish. For the user interface, it will pick up the language you have set EDMC to use. If anyone would like to help translate into other languages, please post a message on the BGS-Tally Discord.
* Independent language for Discord posts. You can separately set the language that is used for Discord posts, in case the Discord server has a different preferred language to the one you run EDMC in.
* Added logo to main window and all window icons
* Added options to only post your BGS activity, only your TW activity or both (defaults to both), for CMDRs who want to selectively post a single type of activity.
* Now track and report Search and Rescue (SandR) hand-ins for the BGS, tallied against the controlling faction at the station handed in.
* Now track side objectives in space conflict zones, but with some caveats:
    * Capital ship defeats 👑 should be 100% reliable
    * Spec ops wing kills 🔠 are tallied as soon as BGS-Tally finds the **first detectable kill** in the spec ops wing. This may not be the first spec ops kill you make because the order of events logged by the game is not predictable, so we need to tally as soon as we spot a kill. Just make sure you finish off those spec ops wings CMDRs!
    * Enemy captain kills 👨‍✈️ will sometimes be tallied and sometimes not, for the same reason.
    * Enemy propagandist wing kills ✒️ are also tallied as soon as BGS-Tally spots the **first detectable kill** in the propagandist wing, for the same reason.
* Added tooltips (hover text) to all abbreviations on screen, and a few of the controls and buttons that are not self-explanatory.
* Added support for different Discord post formats. So if your squadron or group would like your discord activity posts to look different, this can be done. Currently it's a programming job to create a new format (so ask your friendly Python developer to get in touch, or send in a suggestion for a new format to the BGS-Tally Discord server).
* Added popup CMDR information on the in-game overlay when you interact with a CMDR.
* Added 'Copy to Clipboard' button on CMDRs information window.

### Changes:

* Added new logo as avatar for all posts.
* Removed 'modified by Aussi' references, as Tez (the original author of BGS-Tally) is now recommending this version to users.
* Each trade buy / sell band is only reported if it is non-zero, avoiding clutter in the report.
* Changed the font used in the Discord preview panel on activity windows to a font that supports more emoji and more closely matches Discord posts.
* Tweaked the discord webhooks layout in settings to include horizontal lines for better clarity.
* Unfortunately had to remove the functionality to log CMDRs scanned while in a dropship / taxi as we can no longer get the CMDR name from the game journal.
* The layout of the CMDR information panel in the CMDRs window has been tidied up.

### Bug Fixes:

* Thargoid War VIP passenger evac missions weren't being counted.
* Was incorrectly reporting BGS activity in TW systems.
* Was incorrectly reporting TW search and rescue collection in non-TW systems.
* Activity window wasn't showing all trade purchase and profit bands.
* If you changed your Discord webhook settings after previously successfully posting to Discord, then tried to post again in the same tick, it would fail.
* If any Discord post got bigger than the limits imposed by Discord, it would silently fail to post. Now, the post is truncated to the Discord limit and '...' appended to the end.
* The 'Post to Discord' button on the CMDRs information window was sometimes becoming enabled even if there were no valid discord webhooks set up.

### API Changes ([vx.x](https://studio-ws.apicur.io/sharing/xxxxxxxx)):

* `/activities` endpoint: Search and Rescue handins now included at `systems/[system]/factions/[faction]/sandr`, containing `damagedpods`, `occupiedpods`, `thargoidpods`, `blackboxes`, `wreckagecomponents`, `personaleffects`, `politicalprisoners` and `hostages` as properties.


## v3.6.1 - 2024-04-07

### Bug Fixes:

* For some CMDRS, TW system and station data was omitted for some systems.


## v3.6.0 - 2024-03-23

### New Features:

* BGS-Tally now tracks carrier commodity buy and sell orders (in addition to the existing bartender materials buy and sell orders). These are tracked in real time as you change your carrier orders. They are posted to Discord with your materials orders.
* You can now pin one or more systems to the in-game overlay, to permanently show your work in those systems.
* Adding a friend is now logged as a CMDR interaction.
* Thargoid Titan bio pod collection and hand-in tracking 🏮. You can hand them in at any rescue ship, but they are tallied in the system they were collected.
* If you accidentally target an ally ship in a space CZ, you now get a warning on screen.

### Changes:

* The tracking of bartender materials buy and sell orders is now updated in real time, as you change them in your carrier. Previously, you would have to wait for the next CAPI carrier data update, which would be at the most every 15 minutes.
* The Carrier information window has been reorganised to show commodities and materials.
* All 'Post to Discord' buttons now only allow a single click. They temporarily disable themselves for a few seconds after posting, to avoid accidental multiple posts.
* No longer report BGS work for systems in Thargoid War.
* Activity windows no longer show BGS factions and data for Thargoid War systems, instead now showing a message stating that the system is in TW state.
* Activity windows no longer show a spurious 'Enable' checkbox (which didn't do anything) for systems that have no factions, instead now showing a message stating it is an empty system.

### Bug Fixes:

* Wasn't omitting BGS activity from systems in TW state in 'modern' style Discord posts, only text posts. Now omitted in both.
* Not all thargoid activity was being omitted when a system was switched off.
* A lot of special characters used in TW reports were not displaying correctly in the in-game overlay.
* Fixed a rare crash that would stop the in-game overlay working.
* Sometimes BGS-Tally wasn't realising you had left a megaship scenario.

### API Changes ([v1.4](https://studio-ws.apicur.io/sharing/3164656a-eea9-4588-a9b9-e3f5f7ee66bc)):

* `/activities` endpoint: Added `thargoidpods` to `systems/[system]/twsandr`.


## v3.5.0 - 2024-02-27

### New Features:

* New 'detailed INF' report. This is optional and is off by default, but when enabled gives a detailed breakdown of the number of missions completed at each +INF level. For example: `INF +19 (➋ x 4 ➌ x 2 ➎ x 1)` means you completed 4 missions awarding ++, 2 mission awarding +++ and 1 mission awarding +++++. Manually tallied INF is simply added or removed from the overall total.
* When secondary INF reporting is switched on, now indicate which INF is primary `🅟` and which is secondary `🅢`. This can also combine with detailed INF reporting to give a full breakdown of primary and secondary INF.
* New 'detailed Trade' checkbox, which is on by default and when enabled shows the full trade breakdown into brackets 🆉 | 🅻 | 🅼 | 🅷, when disabled all brackets are combined into simple totals for trade purchase and trade profit.
* When multiple CMDRs are selected in the CMDR window, 'Post to Discord' now posts a concise table containing all the CMDRs in the list, with Inara and Inara squadron links where available. With a single CMDR selected, posting is exactly the same as it was.

### Changes:

* Activity windows (latest Tally / previous Tally) will now remember their positions within a game session. Height and width is still automatic to avoid truncated content if it's larger than the last time you opened the window.
* Re-opening an already open activity window (latest Tally / previous Tally) will no longer open two copies of the same window. Instead, the old one will be closed and a new fresh window with latest data opened at the same position and size on screen.


## v3.4.0 - 2024-02-09

### New Features:

* Discord webhooks completely re-worked. Now, instead of a single, fixed webhook for each type of Discord post, there is a fully flexible table of webhooks which you can set up any way you like - a single webhook for all Discord posts; a webhook for each type of Discord post; multiple webhooks for each type, or any combination of these. As one example, this would allow you to send your BGS reports to multiple Discord servers if you wish.
* The system title and a link to the Inara page for the system are now shown at the top of every activity panel.

### Changes:

* Heading styles have been standardised across all windows. And headings are now purple, yay!
* URL link styles have been standardised across all windows.
* When posting CMDR info to Discord, now include how you interacted with them, colour coded.
* The 'Post to Discord' button is now always visible (but greyed out if not usable) on Fleet Carrier and CMDR Information windows.

### Bug Fixes:

* Thargoid vessel types in mission reports were still showing if they were 0. These are now omitted.
* Fix error when fetching carrier data when carrier has no sell orders.
* If an `/events` API client sets an event filter using an integer as the filter, e.g. `3`, this was throwing an error and the event was not sent.


## v3.3.0 - 2023-12-09

### New Features:

* Targeting a player in a taxi will now log the player name and attempt lookup on Inara.
* Now log the details of any CMDR who interdicts you, sends a message in local chat, invites you to a team, kills you solo or kills you in a team.
* The CMDR listing window now has an extra 'Interaction' column which describes how you interacted with the other CMDR (scanned, interdicted by etc.).
* Thargoid War banshee kills are now tallied.

### Changes:

* Faction name abbreviations are less obscure when the faction name contains a number or a dash.
* Thargoid vessel types are omitted if they are 0, both for kills and for missions. This creates shorter and clearer reports.
* No longer include Exobiology sales in discord reports.
* Plugin no longer terminates if it cannot fetch the tick from elitebgs.app on initial load. Not an ideal situation as we know nothing about the current tick, but at least BGS-Tally is still usable in this situation.

### Bug Fixes:

* Fix (another) crash in code that detects drop from supercruise at megaships.

### API Changes ([v1.3](https://studio-ws.apicur.io/sharing/d352797e-c40e-4f91-bcd8-773a14f40fc0)):

* `/events` endpoint: All localised fields are now stripped before sending. i.e. fields who's name ends with `_Localised`.
* `/activities` endpoint: Added `banshee` to `systems/[system]/twkills`.
* `/activities` endpoint: Added `scythe-glaive` to `systems/[system]/twkills`.


## v3.2.0 - 2023-10-21

### New Features:

* In-game overlay now briefly displays a BGS summary for the current system when doing BGS work.
* Space Conflict Zones are now tracked automatically. As with Ground CZs, the game doesn't give us enough information to detect whether you've actually **won** the CZ, so if you drop in and log a kill within 5 minutes, this is tallied as a win. Manual controls are still available to adjust if you need.
* Thargoid War system progress is now displayed as a progress bar on the in-game overlay when in a TW active system.
* An activity indicator now briefly flashes green on the overlay when BGS-Tally logs BGS or TW activity.
* Thargoid War reactivation (settlement reboot) missions are now tracked: both for the station issuing the mission (`🛠️ x n missions`) and for the system where the settlement was reactivated (`🛠️ x n settlements`).
* Added a new setting to allow you to switch off reporting for new systems you visit. This is for CMDRs who regularly only want to report a subset of their work - it means you don't have to switch off a load of systems, you can just switch on the few you need.
* Forced ticks are now labelled clearly, including in Discord posts.
* Allow each overlay panel to be individually hidden or shown.
* Automatically attempt to track megaship scenarios.  As with Ground CZs, the game doesn't give us enough information to detect whether you've actually **won** the scenario, so if you drop in and log a kill within 5 minutes, this is tallied as a win for the faction that's at war with the first ship you kill.
* Added quick-setup button for [Comguard](https://comguard.app/) in API configuration window.

### Changes:

* Pop-up legend window now contains a list of the Thargoid vessel type abbreviations.
* Show a hand cursor 👆 over help text to make it clearer you can click it to show the legend window.
* Pop-up legend window now includes 🛠️ for TW reactivation missions.
* Trade purchase is now reported in three brackets rather than two: 🅻 | 🅼 | 🅷
* Trade profit is now reported in four brackets rather than three: 🆉 | 🅻 | 🅼 | 🅷

### Bug Fixes:

* Some Orthrus kills were not being tallied because the bond value logged was 40m instead of the previous 25m. We can only detect the type of Thargoid via the bond value logged by the game, so BGS-Tally will now tally an Orthrus for both kill values.
* Trade purchase, sale and profit was not being logged if you previously disembarked from your ship on foot, took a taxi or dropship somewhere, returned to your ship and then traded.
* Forcing a tick (via the settings panel), though still not recommended unless automatic tick detection has **definitely** missed a tick, should now be much more reliable:
    * It would cause your previously logged activity for the current tick to be lost and replaced by activity after the forced tick. Now, a 'proper' new tick is created so your earlier activity should be kept and available in the previous ticks dropdown menu.
    * If an automatic tick arrived with an earlier tick time than your forced tick, this could cause BGS-Tally to get confused. We now ignore any incoming ticks that have an older tick time than your forced tick.
    * Forced ticks are now handled more elegantly when sending data via the BGS-Tally API, as we generate a fake `tickid` for the forced tick.
* Due to a game bug, some illegal massacre and assassination missions were not tallying negative INF correctly against the target faction. Implemented a workaround for this.
* Due to a game bug, some ship murders were not being tallied against the target ship faction. Implemented a workaround for this.
* BGS-Tally now handles cargo ejection for Thargoid S&R operations. Previously, it could mis-tally to the wrong system because it hadn't realised the cargo scooped in that system had been destroyed by ejection.
* If you quit EDMC, jumped to a new system, then relaunched EDMC, any activity would be tallied to the last system you visited before quitting EDMC. BGS-Tally now realises that you are in a new system. Please note however, although it now knows you're in a new system, it can't get hold of faction or conflict information in this situation, so if you plan to work in the new system and haven't visited it before in this tick, you should jump to another system and back, or re-log to the main menu, either of which will properly load up the factions and conflicts.
* `/events/` API wasn't augmenting `StationFaction` correctly for `MissionFailed` and `MissionAbandoned` events (per API spec v1.1).
* Thargoid S&R operations cargo tracking now cleared down properly when your cargo hold is empty. Previously, it could mis-tally to the wrong system.
* Don't clear Thargoid S&R delivery tally if you are killed.
* Fix crash in code that detects drop from supercruise at megaships.


### API Changes ([v1.2](https://studio-ws.apicur.io/sharing/cc3753c2-6569-4d74-8448-8fb9363898ce)):

* `/activities` endpoint: Thargoid War reactivation missions now included in `systems/[system]/factions/[faction]/stations/[station]/twreactivate`
* `/activities` endpoint: Thargoid War number of settlements reactivated now included in `systems/[system]/twreactivate`
* `/activities` endpoint: `Activity` now has a `ticktime` timestamp in addition to `tickid`.
* `/activities` endpoint: When the user forces a tick, a new `tickid` is generated by BGS-Tally that conforms to the 24-character elitebgs.app tickid standard but starts with six zeroes '000000' to distinguish it as a forced tick.
* `/events` endpoint: `Event` now has a `ticktime` timestamp in addition to `tickid`.
* `/events` endpoint: When the user forces a tick, a new `tickid` is generated by BGS-Tally that conforms to the 24-character elitebgs.app tickid standard but starts with six zeroes '000000' to distinguish it as a forced tick.
* `/events` endpoint: Ensure `StationFaction` is not overwritten if it is already present from the journal event.
* `/events` endpoint **breaking change**: `StationFaction` is now always an object with a single `Name` property, and is never a simple string.


## v3.1.1 - 2023-08-23

### Bug Fixes:

* Fixed the Fleet Carrier screen, which was showing empty buy and sell order panels if your carrier had _either_ no buy or sell orders.


## v3.1.0 - 2023-08-13

### New Features:

* Thargoid War kills are now tracked for each vessel type: `💀 (kills)`. But **please be aware**: BGS-Tally will only count a kill if it is logged in your game journal. This reliably happens if you solo kill a Thargoid, and usually happens (since game update 16) when you kill in a Team or with others.
* Thargoid War Search and Rescue collection and hand-in tracking. BGS-Tally now tracks where you pick up occupied and damaged escape pods ⚰️, black boxes ⬛ and tissue samples 🌱. You can hand them in anywhere, but they are tallied in the system they were collected.
* You can now delete CMDRs from the CMDR target list history.
* Targets older than 90 days are automatically removed from the CMDR target list history.
* When a friend request is received from another player, their details are looked up on Inara and they are added to the target log. Note that the squadron ID and legal status will be shown as '----' as that information is not available for friend requests.
* Carrier jump reporting implemented, automatically reporting your carrier jumps (and cancelled jumps) to a Discord channel of your choice.
* Thargoid War Revenant kills are now tracked (`R` in report).
* Thargoid War Scythe and Glaive kills are now tracked (`S/G` in report).
* Track the new TW evacuation mission released in Update 16.

### Changes:

* Thargoid War massacre missions are now labelled slightly differently - `💀 (missions)` - in line with the labelling for kills - `💀 (kills)`.
* Posting targeted CMDR information on Discord now goes to a separate 'CMDR Information' channel, if you configure one. It will fall back to using the BGS channel.
* Posting information on Discord now goes to a separate 'CMDR Information' channel, if you configure one. It will fall back to using the BGS channel.
* Exploration data tallying now takes into account not just the `TotalEarnings` logged but also the `BaseValue` and `Bonus`. The larger value is used if these differ.  Note this is now the same logic that EDDiscovery uses.
* If there is a new version of BGS-Tally available, it is downloaded and prepared during **launch** of the plugin instead of **shutdown**. You still need to relaunch EDMC to get the new version, but this change should mean that if there is a critical plugin bug that kills the plugin, we should be able to fix it with an auto-update.

### Bug Fixes:

* BGS-Tally was crashing on load when running on Linux. This is now fixed.
* Fix failure of networking thread, and therefore all subsequent networking calls, if an API discovery request detects new API features during startup.
* TW kills were not being logged to the correct system if it was a zero-population system. This was because historically BGST only dealt with BGS logging, so ignored zero-pop systems.  We now create tracking entries for these systems.
* Harden all file loading and JSON parsing to protect against corrupted data on disk.
* Potential fix for mis-tallying of ground CZs when other commanders are fighting.
* Check for main UI frame before attempting to update the status text. Protects against rare errors where the status bar was updated before the main window has fully initialised.

### API Changes ([v1.1](https://studio-ws.apicur.io/sharing/c2adeddc-f874-42d3-b450-49bd59ed1a79)):

* `/activities` endpoint: Thargoid war kills now included in `systems/[system]/twkills`
* `/activities` endpoint: Thargoid search and rescue counts now included in `systems/[system]/twsandr`
* `/events` endpoint: `StationFaction` is now an empty string "" when undocked.


## v3.0.2 - 2023-04-11

### Bug Fixes:

* Fix crashing bug which was affecting some CMDRs, stopping Discord posting. Unfortunate side effect was that it also stopped auto-updating, so this version will have to be installed manually.


## v3.0.1 - 2023-04-11

### Bug Fixes:

* Trade purchasing at 'High' supply stock bracket wasn't being reported.


## v3.0.0 - 2023-04-09

### New Features:

* Plugin auto-update. From this version on, when a new version of the plugin is released, it will automatically be downloaded and update itself the next time you launch EDMarketConnector. You will need to install this version 3.0.0 manually, but that should be the last time you ever have to do a manual update unless you want to test pre-release versions (i.e. alphas or betas).
* Fleet Carrier materials tracking. BGS-Tally will now track your fleet carrier materials for sale and for purchase, with the ability to post to Discord. For this to work, you need to be using EDMC v5.8.0 or greater, authenticate EDMC with your Frontier account, own a fleet carrier (!) and visit your fleet carrier management screen in-game.
* API. This allows BGS-Tally to send data to a server of your choice, to allow your squadron or another player group to collect and analyse your activity. If the server provides information about itself, this is shown to you and you are **always explicitly asked** to approve the connection.
* On-foot murders are now tracked and are independent from ship murders.
* Trade demand. Trade purchase and profit is now tracked and reported against the levels of demand: 🅻 / 🅷 for purchases and 🆉 / 🅻 / 🅷 for sales (🆉 is zero demand, i.e. when you sell cargo that the market doesn't list).
* In-game overlay: The tick warning has been enhanced, with various levels depending on when the last tick was.
* Legend. There is now a key / legend popup showing all the various Discord icons used in reports and what they mean. Access this by clicking the ❓ icon in any activity window.
* New Discord preview. The Discord preview has been completely re-worked to much more closely match the look and colouring of the final Discord post.

### Changes:

* Limit the 'Previous Ticks' dropdown to just the last 20 activity logs. Previous logs are still available, find them in `activitydata/archive/` in the BGS-Tally folder.
* Old `Today data.txt` and `Yesterday Data.txt` files from previous versions of BGS-Tally will now be deleted if found (after conversion to latest format).
* BGS-Tally is now more efficient in saving changes to activity files - it only saves to disk when something has changed or you have done some activity in a tick.
* Plugin name and plugin foldername are now properly separated, so if you change the plugin's folder name, Inara API calls and the plugin name in Discord posts will still correctly say 'BGS-Tally'.
* The plain text Discord post text now has the plugin name and version included in the footer.
* Re-worked the way BGS-Tally makes network requests, so they are now able to be queued and handled in a background thread. This means the plugin won't lock up EDMC if it's waiting for a slow response from a server. Migrating existing requests will be done in stages. So far, Inara requests when scanning CMDRs, all Discord posting, and all API requests are done in the background.
* Discord changed its colour scheme for code blocks to be largely light blue and white, so re-worked all Discord posts to use new colours (`ansi` blocks instead of `css`).
* Sizing and layout of activity window has been reworked so the window is always the optimum size.

### Bug Fixes:

* In-game overlay: Fixed occasional flickering of the tick time.
* No longer allow multiple copies of the CMDRs list window to be opened at the same time.
* No longer carry forward the contents of the notes field from one tick to the next.
* Fixed rare problem where trying to save activity data when the tickID is invalid.
* Fixed very rare and unusual bug where ground settlement data was invalid, killing the tally window.
* No longer perform any journal processing if game is a public beta test version.
* Ensure buttons in activity window don't get overwritten by other content.


## v2.2.1 - 2023-01-04

### Bug Fixes:

* The CMDR list window wasn't listing scanned commanders. This was due to a missing config file, which should have contained the Inara API key. DOH!
* In some circumstances, Thargoid War mission counts and commodity / passenger counts could be over-inflated. This is now fixed.


## v2.2.0 - 2023-01-02

### New Features:

* Thargoid War mission tracking 🍀. BGS-Tally now tracks your Thargoid War passenger 🧍, cargo 📦, injured ⚕️, wounded ❕ and critically wounded ❗ (escape pod) missions as well as Thargoid Massacre Missions for each Thargoid vessel type. There are options to report just BGS, just Thargoid War or all combined activity, as well as an option to have a separate Discord channel when reporting Thargoid War activity.
* Additional notes field. There is a new text field in the activity window to allow you to add notes and comments to your Discord post(s).

### Changes:

* When displaying information about a CMDR, or posting to Discord, use the latest information we know about that CMDR (squadron membership, for example).
* When displaying CMDR ship type, try to use the localised name if present, instead of internal ship name (e.g. `Type-10 Defender` instead of `type9_military`).
* The text report field is no longer manually editable. Keeping this editable wasn't possible with the splitting of the reports into BGS and Thargoid War, and was a bit of an oddity anyway, as it only worked for legacy (text) format posts and also any edits were always overwritten by any changes and lost when the window was closed. If you need to edit your post, copy it and edit it at the destination after pasting. Note that the new Discord Notes field (see above) now allows you to add comments to your posts, and these are stored between sessions.
* When listing ground CZs, use a ⚔️ icon against each to easily differentiate them.
* Tweaks to post titles and footers.
* Whitespace is now stripped from Discord URLs to minimise user error (thanks @steaksauce-).
* The 'Post to Discord' button is now enabled / disabled rather than hidden completely.

### Bug Fixes:

* If a selected CMDR has a squadron tag, but that squadron isn't available in Inara, still show the tag when displaying or posting the CMDR info to Discord.
* Moved the overlay text - both tick time and tick alerts - a little to the left to allow for differences in text placement between machines.
* When using new modern Discord format, don't create empty posts and delete previous post if content is empty.
* Minor change to 'CMDRs' button image to make it clearer in dark mode.
* A limit of 60 is now applied to the number of tabs shown in the activity window, as too many tabs could crash the plugin.
* Latest activity window would fail to display if a file is expected on disk but it has been deleted. In this circumstance, just clear down and start from zero.
* When a new tick is detected, we now ensure that there is a tab displayed for the player's current system in the new window, so activity can be logged straight after the tick.


## v2.1.0 - 2022-12-05

### New Features:

* CMDR Spotting. The plugin now keeps track of the players you target and scan, together with when it happened and in which system. It also looks up any public CMDR and Squadron information on Inara. All this information is presented in a new window where you can review the list of all CMDRs you've targeted. There is also a 'Post to Discord' feature so you can post the CMDR information to your Discord server if you wish (manual only).
* New format available for Discord posts. The (I think) neater and clearer look uses Discord message embeds. The old text-only format is still available from the settings if you prefer it.

### Changes:

* After the game mode split in Odyssey Update 14, BGS-Tally only operates in `Live` game mode, not `Legacy`.
* Additional data files created by BGS-Tally (such as the mission log) are now saved in an `otherdata` subfolder to keep the top level folder as tidy as possible.

### Bug Fixes:

* BGS-Tally was intentionally omitting secondary INF when a faction was in conflict, but it turns out some mission types can have -ve INF effects on those factions. So we now report all secondary INF.
* The game was not including expiry dates in some mission types (why?), and BGS-Tally was throwing errors when it encountered these. Now we don't require an expiry date.


## v2.0.2 - 2022-10-27

### Bug Fixes:

* Some state was not being initialised correctly on first install of BGS-Tally.


## v2.0.1 - 2022-10-22

### Bug Fixes:

* The latest activity window was failing to display on a clean install of BGS-Tally.


## v2.0.0 - 2022-10-22

### New Features:

* In game overlay implemented!  Currently this just displays the current tick time, and if the next predicted tick is in the next hour, will alert that it's upcoming. The overlay requires *either* installing the separate [EDMCOverlay plugin from here](https://github.com/inorton/EDMCOverlay/releases/latest) *or* having another plugin running that has EDMCOverlay built in (for example the EDR plugin). _Many more things are planned for the overlay in future versions of BGS-Tally_.
* In the activity window, there are now markers against every system, showing at a glance whether there is activity (&#129001; / &#11036;) and also whether you are reporting all, some, or none of the activity (&#9745; / &#9632; / &#9633;).
* The system you are currently in is always displayed as the first tab in the activity log, whether or not you've done any activity in it and whether or not you have "Show Inactive Systems" switched on. This allows you to always add activity manually in the system you're in, e.g. Space CZ wins.
* The 'Previous BGS Tally' button has been replaced by a 'Previous BGS Tallies &#x25bc;' selector, where you can look at all your history of previous work.

### Changes:

* Changed the tick date / time format in main EDMC window to make it more compact.
* Changed the date / time format in Discord posts to avoid localised text (days of week and month names).
* Big improvement in detecting new ticks. Previously, it would only check when you jump to a new system. Now, it checks every minute. This means that even if you stay in the same place (e.g. doing multiple CZs in one system), the tick should tock correctly.
* This version includes a complete and fundamental rewrite of the code for ease of maintenance. This includes a change in how activity is stored on disk - the plugin is now no longer limited to just 'Latest' and 'Previous' activity, but activity logs are kept for many previous ticks - all stored in the `activitydata` folder.
* Revamped the plugin settings panel.

### Bug Fixes:

* Murders were being counted against the system faction. Now count them against the faction of the target ship instead.
* Using the mini scroll-left and scroll-right arrows in the tab bar was throwing errors if there weren't enough tabs to scroll.
* A full fix has now been implemented to work around the game bug where the game reports an odd number of factions in conflicts in a system (1, 3, 5 etc.) which is obviously not possible. BGS-Tally now pairs up factions, and ignores any conflicts that only have a single faction.


## v1.10.0 - 2022-08-11

### New Features:

* Now use scrollable tabs and a drop-down tab selector. Tabs for systems are sorted alphabetically by name, prioritising systems that have any BGS activity first.
* Every Discord post now includes a date and time at the bottom of the post, to make it clear exactly when the user posted (suggested by @Tobytoolbag)
* There is now a 'Force Tick' button in the settings, which can be used if the tick detector has failed to detect a tick but you know one has happened. This can occur on patch days or if the tick detector is down.

### Changes:

* Now use an automated GitHub action to build the zip file on every new release.
* Tidy up and narrow the BGS-Tally display in the EDMC main window, to reduce the width used (thank you @Athanasius for this change).

### Bug Fixes:

* Workaround for game bug where factions are incorrectly reported at war (if only a single faction is reported at war in a system, ignore the war) now works for elections too.


## v1.9.0 - 2022-04-23

### New Features:

* Now track Scenario wins (Megaship / Space Installation) - unfortunately manual tracking only, because we cannot track these automatically.

### Bug Fixes:

* If a faction state changed post-tick, this was not spotted by the plugin if you have already visited the system since the tick. Most noticeable case was when a war starts if you were already in the system - no CZ tallies or manual controls appeared. This is fixed.
* Better handling of network failures (when plugin version checking and tick checking).
* Now accepts Discord webhooks that reference more domains: `discord.com`, `discordapp.com`, `ptb.discord.com`, `canary.discord.com`. This was stopping the _Post to Discord_ button from appearing for some users (thank you @Sakurax64 for this fix).

### Changes:

* Simplified the `README`, moving more information into the wiki.


## v1.8.0 - 2022-02-23

### New Features:

* Now track Black Market trading separately to normal trading.
* Now track trade purchases at all markets, as buying commodities now affacts the BGS since Odyssey update 10.

### Bug Fixes:

* Never track on-foot CZs when in Horizons, to help reduce false positives.
* Fix error being thrown to the log when closing EDMC settings panel.
* Add workaround for game bug where factions are incorrectly reported at war - if only a single faction is reported at war in a system, ignore the war.

### Changes:

* Faction name abbreviations are slightly better when dealing with numbers, as they are no longer abbreviated. For example `Nobles of LTT 420` is now shortened to `NoL420` instead of `NoL4`.
* Layout tweaks to the columns in the report windows.


## v1.7.1 - 2021-12-21

### Bug Fixes:

* Fix plugin failure if tick happens while in-game, and you try to hand in BGS work before jumping to another system.


## v1.7.0 - 2021-11-01

### New Features:

* Now track (and report) names of on-foot CZs fought at, automatically determine CZ Low / Med / High, and automatically increment counts. Note that we still can't determine whether you've actually _won_ the CZ, so we count it as a win if you've fought there.
* Now track Exobiology data sold.
* New setting to show/hide tabs for systems that have no BGS activity, default to show.

### Changes:

* Bounty vouchers redeemed on Fleet Carriers now count only 50% of the value.
* Added scrollbar to Discord report.
* When plugin is launched for the very first time, default it to 'Enabled' so it's immediately active.
* Reorganisation and tidy up of settings panel, and add link to help pages.
* The Discord text field and fields in the settings panel now have right-click context menus to Copy, Paste etc.


## v1.6.0 - 2021-10-03

### New Features:

* Now count primary and secondary mission INF separately: Primary INF is for the original mission giving faction and secondary INF is for any target faction(s) affected by the mission. An option is included to exclude secondary INF from the Discord report *
* Discord options are now shown on the main tally windows as well as in the settings.

### Bug Fixes:

* Only count `War` or `Civilwar` missions for the originating faction (thanks @RichardCsiszarik for diagnosing and fixing this).

### Changes:

* Added on-foot scavenger missions and on-foot covert assassination missions to those that count when in `War` or `CivilWar` states.
* Tweaks to window layouts and wording.
* No longer allow mouse wheel to change field values, to help avoid accidental changes.
* Since Odyssey update 7, +INF is now reported for missions for factions in `Election`, `War` and `CivilWar` states. We still report this +INF separately from normal +INF, but have changed the wording to `ElectionINF` / `WarINF` instead of `ElectionMissions` and `WarMissions`.

_* Note that the plugin only tracks primary and secondary INF from this version onwards - all INF in older reports will still be categorised as primary INF._


## v1.5.0 - 2021-09-16

### New features:

* Now count and report certain mission types for factions in the `War` or `CivilWar` states, similarly to how some mission types in `Election` state are counted (gathering a full list of mission types that count when the faction is in conflict is still a work in progress).
* If faction is in state `Election`, `War` or `CivilWar`, don't report fake +INF, instead state the number of election / war missions completed, to avoid confusion.

### Changes:

* Tweaks to window layouts and wording.


## v1.4.0 - 2021-09-09

### New features:

* Can integrate directly with Discord to post messages to a channel, using a user-specified Discord webhook.
* Prefix positive INF with '+'.
* Mission INF is now manually editable as well as automatically updated.
* 'Select all' / 'Select none' checkbox at the top of each system to quickly enable / disable all factions for a system.
* Added 'Failed Missions' to Discord text.

### Bug Fixes:

* Apostrophes in Discord text no longer breaks the colouring.


## v1.3.0 - 2021-09-06

### New features:

* Conflict Zone options are now only presented for factions in `CivilWar` or `War` states.
* The option is now provided to omit individual factions from the report.
* There is a new option in the settings panel to switch on shortening of faction names to their abbreviations. This makes the report less readable but more concise.
* As a suggestion from a user (thanks CMDR Strasnylada!), we now use CSS coloured formatting blocks in the Discord text, which makes it look cleaner and clearer.

### Changes:

* The on-screen layout of the tally table has been improved.


## v1.2.0 - 2021-09-03

### New features:

* Ability to manually add High, Medium and Low on-foot and in-space Combat Zone wins to the Discord report by clicking on-screen buttons.

### Changes:

* Now include a lot more non-violent mission types when counting missions for a faction in the `Election` state (gathering a full list of non-violent mission types is still a work in progress).
* Improvements to layout of window.
* Rename buttons and windows to 'Latest BGS Tally' and 'Previous BGS Tally'.
* The last tick date and time presentation has been improved.


## v1.1.1 - 2021-08-31

### Bug Fixes:

* Now honour the 'Trend' for mission Influence rewards: `UpGood` and `DownGood` are now treated as *+INF* while `UpBad` and `DownBad` are treated as *-INF*.

### Changes:

* Report both +INF and -INF in Discord message.
* Various improvements to README:
    * Improved installation instructions.
    * Added instructions for upgrading from previous version.
    * Added personal data and privacy section.


## v1.1.0 - 2021-08-31

### Changes:

* Changed 'Missions' to 'INF' in Discord text.
* Removed 'Failed Missions' from Discord text.
* Made windows a bit wider to accommodate longer faction names.
* Changed plugin name to just 'BGS Tally' in settings.
* Improvements to the usage instructions in README.
* Renamed buttons to 'Latest Tick Data' and 'Earlier Tick Data' to more clearly describe what each does, avoiding the use of day-based terms 'Yesterday' and 'Today'.


## v1.0.0 - 2021-08-27

Initial release, based on original [BGS-Tally-v2.0 project by tezw21](https://github.com/tezw21/BGS-Tally-v2.0)

### New features:

* Now creates a Discord-ready string for copying and pasting into a Discord chat.
* _Copy to Clipboard_ button to streamline copying the Discord text.

### Bug fixes:

* Typo in 'Missions' fixed

### Other changes:

* Now logs to the EDMC log file, as per latest EDMC documentation recommendations.
