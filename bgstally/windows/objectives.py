import tkinter as tk
from tkinter import ttk

from bgstally.constants import COLOUR_HEADING_1, FONT_HEADING_1, FONT_TEXT
from bgstally.debug import Debug
from bgstally.utils import _, __
from bgstally.widgets import TextPlus
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

        self.txt_objectives: TextPlus = TextPlus(frm_items, wrap=tk.WORD, height=1, font=FONT_TEXT)
        sb_objectives: tk.Scrollbar = tk.Scrollbar(frm_items, orient=tk.VERTICAL, command=self.txt_objectives.yview)
        self.txt_objectives['yscrollcommand'] = sb_objectives.set
        sb_objectives.pack(fill=tk.Y, side=tk.RIGHT)
        self.txt_objectives.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        self.txt_objectives.insert(tk.INSERT, self.bgstally.objectives_manager.get_human_readable_objectives())
        self.txt_objectives.configure(state='disabled')

        self.toplevel.after(5000, self._update_objectives)


    def _update_objectives(self):
        """Refresh the objectives
        """
        self.txt_objectives.configure(state=tk.NORMAL)
        self.txt_objectives.delete('1.0', 'end-1c')
        self.txt_objectives.insert(tk.INSERT, self.bgstally.objectives_manager.get_human_readable_objectives())
        self.txt_objectives.configure(state=tk.DISABLED)

        self.toplevel.after(5000, self._update_objectives)
