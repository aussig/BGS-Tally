import tkinter as tk
from functools import partial
from tkinter import ttk

from bgstally.constants import DiscordChannel, MaterialsCategory
from bgstally.debug import Debug
from bgstally.fleetcarrier import FleetCarrier
from bgstally.ui import UI
from bgstally.widgets import TextPlus


class WindowFleetCarrier:
    """
    Handles the Fleet Carrier window
    """

    def __init__(self, bgstally, ui: UI):
        self.bgstally = bgstally
        self.ui: UI = ui

        self._show()


    def _show(self):
        """
        Show our window
        """
        window = tk.Toplevel(self.ui.frame)
        window.title(f"Fleet Carrier Information for Carrier {self.bgstally.fleet_carrier.name}")
        window.geometry("600x800")

        container_frame = ttk.Frame(window)
        container_frame.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.Frame(container_frame)
        info_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        buttons_frame = ttk.Frame(container_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        ttk.Label(info_frame, text=f"Fleet Carrier Information for Carrier {self.bgstally.fleet_carrier.name}", font=self.ui.heading_font, foreground='#A300A3').pack(anchor=tk.NW)
        ttk.Label(info_frame, text="Selling", font=self.ui.heading_font).pack(anchor=tk.NW)
        selling_frame = ttk.Frame(info_frame)
        selling_frame.pack(fill=tk.BOTH, padx=5, pady=5, anchor=tk.NW, expand=True)
        selling_text = TextPlus(selling_frame, wrap=tk.WORD, height=1, font=("Helvetica", 9))
        selling_scroll = tk.Scrollbar(selling_frame, orient=tk.VERTICAL, command=selling_text.yview)
        selling_text['yscrollcommand'] = selling_scroll.set
        selling_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        selling_text.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        selling_text.insert(tk.INSERT, self.bgstally.fleet_carrier.get_materials_plaintext(MaterialsCategory.SELLING))
        selling_text.configure(state='disabled')


        ttk.Label(info_frame, text="Buying", font=self.ui.heading_font).pack(anchor=tk.NW)
        buying_frame = ttk.Frame(info_frame)
        buying_frame.pack(fill=tk.BOTH, padx=5, pady=5, anchor=tk.NW, expand=True)
        buying_text = TextPlus(buying_frame, wrap=tk.WORD, height=1, font=("Helvetica", 9))
        buying_scroll = tk.Scrollbar(buying_frame, orient=tk.VERTICAL, command=buying_text.yview)
        buying_text['yscrollcommand'] = buying_scroll.set
        buying_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        buying_text.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        buying_text.insert(tk.INSERT, self.bgstally.fleet_carrier.get_materials_plaintext(MaterialsCategory.BUYING))
        buying_text.configure(state='disabled')

        if self.bgstally.discord.is_webhook_valid(DiscordChannel.FLEETCARRIER): ttk.Button(buttons_frame, text="Post to Discord", command=partial(self._post_to_discord)).pack(side=tk.RIGHT, padx=5, pady=5)


    def _post_to_discord(self):
        """
        Post Fleet Carrier materials list to Discord
        """
        title = f"Materials List for Carrier {self.bgstally.fleet_carrier.name}"
        description = f"**Selling:**\n```css\n\n{self.bgstally.fleet_carrier.get_materials_plaintext(MaterialsCategory.SELLING)}```\n**Buying:**\n```css\n\n{self.bgstally.fleet_carrier.get_materials_plaintext(MaterialsCategory.BUYING)}```"

        self.bgstally.discord.post_embed(title, description, None, None, DiscordChannel.FLEETCARRIER)


