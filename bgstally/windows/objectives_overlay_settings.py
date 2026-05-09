import sys
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

from bgstally.constants import COLOUR_HEADING_1, FONT_HEADING_2
from bgstally.utils import _


class WindowObjectivesOverlaySettings:
    """
    Handles a window for configuring objectives overlay display modes
    """

    def __init__(self, bgstally: 'BGSTally'):
        self.bgstally: BGSTally = bgstally
        self.toplevel: tk.Toplevel = None
        self.temp_mode: tk.StringVar = None


    def show(self, parent_frame: tk.Frame = None):
        """
        Show the window
        """
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            self.toplevel.focus()
            return

        if parent_frame is None:
            parent_frame = self.bgstally.ui.frame

        self.toplevel: tk.Toplevel = tk.Toplevel(parent_frame)
        self.toplevel.title(_("{plugin_name} - Objectives Overlay Settings").format(plugin_name=self.bgstally.plugin_name)) # LANG: Objectives overlay settings window title
        self.toplevel.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.toplevel.geometry("700x550")
        self.toplevel.resizable(False, False)

        if sys.platform == 'win32':
            self.toplevel.attributes('-toolwindow', tk.TRUE)

        # Create a temporary variable to hold the selection until Save is clicked
        self.temp_mode = tk.StringVar(value=self.bgstally.state.OverlayObjectivesMode.get())

        frame_container: ttk.Frame = ttk.Frame(self.toplevel, padding=15)
        frame_container.pack(fill=tk.BOTH, expand=tk.YES)

        current_row: int = 0

        # Title
        tk.Label(frame_container, text=_("Objectives Overlay Display Mode"), font=FONT_HEADING_2, foreground=COLOUR_HEADING_1).grid( # LANG: Label on objectives overlay settings window
            row=current_row, column=0, sticky=tk.W, pady=(0, 10))
        current_row += 1

        # Description
        tk.Label(frame_container, text=_("Choose how objectives are displayed in the in-game overlay:"), wraplength=650, justify=tk.LEFT).grid( # LANG: Label on objectives overlay settings window
            row=current_row, column=0, sticky=tk.W, pady=(0, 15))
        current_row += 1

        # Mode 0: Notification
        tk.Radiobutton(
            frame_container,
            text=_("Show notification for new objectives"),  # LANG: Radio button on objectives overlay settings window
            variable=self.temp_mode,
            value="0"
        ).grid(row=current_row, column=0, sticky=tk.W, pady=2)
        current_row += 1
        tk.Label(frame_container, text="     " + _("Shows a notification when a new objective is detected"), # LANG: Label on objectives overlay settings window
                 wraplength=650, justify=tk.LEFT, foreground="gray").grid(
            row=current_row, column=0, sticky=tk.W, pady=(0, 8))
        current_row += 1

        # Mode 1: New objectives
        tk.Radiobutton(
            frame_container,
            text=_("Show new objective"), # LANG: Radio button on objectives overlay settings window
            variable=self.temp_mode,
            value="1"
        ).grid(row=current_row, column=0, sticky=tk.W, pady=2)
        current_row += 1
        tk.Label(frame_container, text="     " + _("Shows objective details when a new objective is detected."), # LANG: Label on objectives overlay settings window
                 wraplength=650, justify=tk.LEFT, foreground="gray").grid(
            row=current_row, column=0, sticky=tk.W, pady=(0, 8))
        current_row += 1

        # Mode 2: New and updated objectives
        tk.Radiobutton(
            frame_container,
            text=_("Show new and updated objectives"), # LANG: Radio button on objectives overlay settings window
            variable=self.temp_mode,
            value="2"
        ).grid(row=current_row, column=0, sticky=tk.W, pady=2)
        current_row += 1
        tk.Label(frame_container, text="     " + _("Shows objective details when an objective and/or their target is added or updated."), # LANG: Label on objectives overlay settings window
                 wraplength=650, justify=tk.LEFT, foreground="gray").grid(
            row=current_row, column=0, sticky=tk.W, pady=(0, 8))
        current_row += 1

        # Mode 3: Always show top priority
        tk.Radiobutton(
            frame_container,
            text=_("Always show top priority objective"), # LANG: Radio button on objectives overlay settings window
            variable=self.temp_mode,
            value="3"
        ).grid(row=current_row, column=0, sticky=tk.W, pady=2)
        current_row += 1
        tk.Label(frame_container, text="     " + _("Always displays the highest priority objective between the active ones."), # LANG: Label on objectives overlay settings window
                 wraplength=650, justify=tk.LEFT, foreground="gray").grid(
            row=current_row, column=0, sticky=tk.W, pady=(0, 8))
        current_row += 1

        # Mode 4: Show all objectives
        tk.Radiobutton(
            frame_container,
            text=_("Always show all objectives"), # LANG: Radio button on objectives overlay settings window
            variable=self.temp_mode,
            value="4"
        ).grid(row=current_row, column=0, sticky=tk.W, pady=2)
        current_row += 1
        tk.Label(frame_container, text="     " + _("Shows all objectives."), # LANG: Label on objectives overlay settings window
                 wraplength=650, justify=tk.LEFT, foreground="gray").grid(
            row=current_row, column=0, sticky=tk.W, pady=(0, 15))
        current_row += 1

        # Buttons frame
        button_frame: ttk.Frame = ttk.Frame(frame_container)
        button_frame.grid(row=current_row, column=0, sticky=tk.E, pady=(10, 0))

        ttk.Button(button_frame, text=_("Cancel"), command=self._cancel).pack(side=tk.RIGHT, padx=(5, 0)) # LANG: Button on objectives overlay settings window
        ttk.Button(button_frame, text=_("Save"), command=self._save).pack(side=tk.RIGHT) # LANG: Button on objectives overlay settings window


    def _save(self):
        """
        Save the selected mode and close the window
        """
        self.bgstally.state.OverlayObjectivesMode.set(self.temp_mode.get())
        self.bgstally.state.save()
        self.bgstally.state.refresh()
        self.toplevel.destroy()
        self.toplevel = None


    def _cancel(self):
        """
        Close the window without saving
        """
        self.toplevel.destroy()
        self.toplevel = None
