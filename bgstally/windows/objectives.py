import tkinter as tk
from functools import partial
from tkinter import ttk

from bgstally.constants import (COLOUR_HEADING_1, COLOUR_WARNING, FONT_HEADING_1, FONT_HEADING_2, FONT_TEXT, DiscordChannel)
from bgstally.debug import Debug
from bgstally.utils import _, __
from config import config
from thirdparty.colors import *


class WindowObjectives:
    """
    Handles the Objectives window
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.toplevel: tk.Toplevel = None


    def show(self):
        """
        Show our window
        """
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            return

        self.toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.toplevel.title(_("{plugin_name} - Objectives").format(plugin_name=self.bgstally.plugin_name, )) # LANG: Objectives window title
        self.toplevel.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.toplevel.geometry("800x800")

        frm_container: ttk.Frame = ttk.Frame(self.toplevel)
        frm_container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm_container, text=_("Objectives"), font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).pack(anchor=tk.NW) # LANG: Label on objectives window

        frm_items: ttk.Frame = ttk.Frame(frm_container)
        frm_items.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        current_row: int = 0

