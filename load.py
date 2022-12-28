from os import path

from companion import CAPIData

from bgstally.bgstally import BGSTally
from bgstally.debug import Debug
from bgstally.constants import UpdateUIPolicy

import semantic_version

PLUGIN_VERSION = semantic_version.Version.coerce("2.2.0-b1")

# Initialise the main plugin class
this:BGSTally = BGSTally(path.basename(path.dirname(__file__)), PLUGIN_VERSION)


def plugin_start3(plugin_dir):
    """
    Load this plugin into EDMC
    """
    this.plugin_start(plugin_dir)

    version_success = this.check_version()
    tick_success = this.check_tick(UpdateUIPolicy.NEVER)

    if tick_success == None:
        # Cannot continue if we couldn't fetch a tick
        raise Exception("BGS-Tally couldn't continue because the current tick could not be fetched")

    return this.plugin_name


def plugin_stop():
    """
    EDMC is closing
    """
    this.plugin_stop()


def plugin_app(parent):
    """
    Return a TK Frame for adding to the EDMC main window
    """
    return this.ui.get_plugin_frame(parent, this.git_version)


def plugin_prefs(parent, cmdr, is_beta):
    """
    Return a TK Frame for adding to the EDMC settings dialog
    """
    return this.ui.get_prefs_frame(parent)


def journal_entry(cmdr, is_beta, system, station, entry, state):
    """
    Parse an incoming journal entry and store the data we need
    """
    if this.state.Status.get() != "Active": return
    this.journal_entry(cmdr, is_beta, system, station, entry, state)


def capi_fleetcarrier(data: CAPIData):
    """
    Handle Fleet carrier data
    """
    if this.state.Status.get() != "Active": return
    this.capi_fleetcarrier(data)
