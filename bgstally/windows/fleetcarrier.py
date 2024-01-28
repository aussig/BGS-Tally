import tkinter as tk
from functools import partial
from tkinter import ttk

from bgstally.constants import COLOUR_HEADING_1, FONT_HEADING_1, FONT_HEADING_2, DiscordChannel, MaterialsCategory
from bgstally.debug import Debug
from bgstally.fleetcarrier import FleetCarrier
from bgstally.widgets import TextPlus
from thirdparty.colors import *


class WindowFleetCarrier:
    """
    Handles the Fleet Carrier window
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.toplevel:tk.Toplevel = None


    def show(self):
        """
        Show our window
        """
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            return

        fc: FleetCarrier = self.bgstally.fleet_carrier

        self.toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.toplevel.title(f"Carrier {fc.name} ({fc.callsign}) in system: {fc.data['currentStarSystem']}")
        self.toplevel.geometry("600x800")

        container_frame = ttk.Frame(self.toplevel)
        container_frame.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.Frame(container_frame)
        info_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        buttons_frame = ttk.Frame(container_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        ttk.Label(info_frame, text=f"System: {fc.data['currentStarSystem']} - Docking: {fc.human_format_dockingaccess()} - Notorious Allowed: {fc.human_format_notorious()}", font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).pack(anchor=tk.NW)
        ttk.Label(info_frame, text="Selling", font=FONT_HEADING_2).pack(anchor=tk.NW)
        selling_frame = ttk.Frame(info_frame)
        selling_frame.pack(fill=tk.BOTH, padx=5, pady=5, anchor=tk.NW, expand=True)
        selling_text = TextPlus(selling_frame, wrap=tk.WORD, height=1, font=("Helvetica", 9))
        selling_scroll = tk.Scrollbar(selling_frame, orient=tk.VERTICAL, command=selling_text.yview)
        selling_text['yscrollcommand'] = selling_scroll.set
        selling_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        selling_text.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        selling_text.insert(tk.INSERT, fc.get_materials_plaintext(MaterialsCategory.SELLING))
        selling_text.configure(state='disabled')


        ttk.Label(info_frame, text="Buying", font=FONT_HEADING_2).pack(anchor=tk.NW)
        buying_frame = ttk.Frame(info_frame)
        buying_frame.pack(fill=tk.BOTH, padx=5, pady=5, anchor=tk.NW, expand=True)
        buying_text = TextPlus(buying_frame, wrap=tk.WORD, height=1, font=("Helvetica", 9))
        buying_scroll = tk.Scrollbar(buying_frame, orient=tk.VERTICAL, command=buying_text.yview)
        buying_text['yscrollcommand'] = buying_scroll.set
        buying_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        buying_text.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        buying_text.insert(tk.INSERT, fc.get_materials_plaintext(MaterialsCategory.BUYING))
        buying_text.configure(state='disabled')

        if self.bgstally.discord.is_webhook_valid(DiscordChannel.FLEETCARRIER_MATERIALS): ttk.Button(buttons_frame, text="Post to Discord", command=partial(self._post_to_discord)).pack(side=tk.RIGHT, padx=5, pady=5)


    def _post_to_discord(self):
        """
        Post Fleet Carrier materials list to Discord
        """
        fc:FleetCarrier = self.bgstally.fleet_carrier

        title:str = f"Materials List for Carrier {fc.name} in system: {fc.data['currentStarSystem']}"
        description:str = ""
        selling:str = fc.get_materials_plaintext(MaterialsCategory.SELLING)
        buying:str = fc.get_materials_plaintext(MaterialsCategory.BUYING)

        if selling != "":
            description += f"**Selling:**\n```css\n{selling}```\n"
        if buying != "":
            description += f"**Buying:**\n```css\n{buying}```\n"

        fields = []
        fields.append({'name': "System", 'value': fc.data['currentStarSystem'], 'inline': True})
        fields.append({'name': "Docking", 'value': fc.human_format_dockingaccess(), 'inline': True})
        fields.append({'name': "Notorious Access", 'value': fc.human_format_notorious(), 'inline': True})

        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)
