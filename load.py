from os import path

import semantic_version
from companion import CAPIData

from bgstally.bgstally import BGSTally
from bgstally.constants import UpdateUIPolicy
from bgstally.debug import Debug

PLUGIN_NAME = "BGS-Tally"
PLUGIN_VERSION = semantic_version.Version.coerce("3.5.0-dev")

# Initialise the main plugin class
this:BGSTally = BGSTally(PLUGIN_NAME, PLUGIN_VERSION)


def plugin_start3(plugin_dir):
    """
    Load this plugin into EDMC
    """
    this.plugin_start(plugin_dir)

    this.check_tick(UpdateUIPolicy.NEVER)

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
    return this.ui.get_plugin_frame(parent)


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
