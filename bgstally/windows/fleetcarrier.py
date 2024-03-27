import tkinter as tk
from functools import partial
from tkinter import ttk

from bgstally.constants import COLOUR_HEADING_1, FONT_HEADING_1, FONT_HEADING_2, FONT_TEXT, DiscordChannel, FleetCarrierItemType
from bgstally.debug import Debug
from bgstally.fleetcarrier import FleetCarrier
from bgstally.utils import _, __
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
        self.toplevel.title(_("%(plugin_name)s - Carrier %(carrier_name)s (%(carrier_callsign)s) in system: %(system_name)s") % {'plugin_name': self.bgstally.plugin_name, 'carrier_name': fc.name, 'carrier_callsign': fc.callsign, 'system_name': fc.data['currentStarSystem']}) # LANG: Carrier window title
        self.toplevel.geometry("600x800")

        container_frame:ttk.Frame = ttk.Frame(self.toplevel)
        container_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container_frame, text=_("System: %(current_system)s - Docking: %(docking_access)s - Notorious Allowed: %(notorious)s") % {'current_system': fc.data['currentStarSystem'], 'docking_access': fc.human_format_dockingaccess(False), 'notorious': fc.human_format_notorious(False)}, font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).pack(anchor=tk.NW) # LANG: Label on carrier window

        items_frame:ttk.Frame = ttk.Frame(container_frame)
        items_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        buttons_frame:ttk.Frame = ttk.Frame(container_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        current_row = 0

        ttk.Label(items_frame, text=_("Selling Materials"), font=FONT_HEADING_2).grid(row=current_row, column=0, sticky=tk.W) # LANG: Label on carrier window
        ttk.Label(items_frame, text=_("Buying Materials"), font=FONT_HEADING_2).grid(row=current_row, column=1, sticky=tk.W) # LANG: Label on carrier window

        current_row += 1

        materials_selling_frame:ttk.Frame = ttk.Frame(items_frame)
        materials_selling_text:TextPlus = TextPlus(materials_selling_frame, wrap=tk.WORD, height=1, font=FONT_TEXT)
        materials_selling_scroll:tk.Scrollbar = tk.Scrollbar(materials_selling_frame, orient=tk.VERTICAL, command=materials_selling_text.yview)
        materials_selling_text['yscrollcommand'] = materials_selling_scroll.set
        materials_selling_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        materials_selling_text.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        materials_selling_text.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_SELLING))
        materials_selling_text.configure(state='disabled')
        materials_selling_frame.grid(row=current_row, column=0, sticky=tk.NSEW)

        materials_buying_frame:ttk.Frame = ttk.Frame(items_frame)
        materials_buying_text:TextPlus = TextPlus(materials_buying_frame, wrap=tk.WORD, height=1, font=FONT_TEXT)
        materials_buying_scroll:tk.Scrollbar = tk.Scrollbar(materials_buying_frame, orient=tk.VERTICAL, command=materials_buying_text.yview)
        materials_buying_text['yscrollcommand'] = materials_buying_scroll.set
        materials_buying_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        materials_buying_text.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        materials_buying_text.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_BUYING))
        materials_buying_text.configure(state='disabled')
        materials_buying_frame.grid(row=current_row, column=1, sticky=tk.NSEW)

        current_row += 1

        ttk.Label(items_frame, text=_("Selling Commodities"), font=FONT_HEADING_2).grid(row=current_row, column=0, sticky=tk.W) # LANG: Label on carrier window
        ttk.Label(items_frame, text=_("Buying Commodities"), font=FONT_HEADING_2).grid(row=current_row, column=1, sticky=tk.W) # LANG: Label on carrier window

        current_row += 1

        commodities_selling_frame:ttk.Frame = ttk.Frame(items_frame)
        commodities_selling_text:TextPlus = TextPlus(commodities_selling_frame, wrap=tk.WORD, height=1, font=FONT_TEXT)
        commodities_selling_scroll:tk.Scrollbar = tk.Scrollbar(commodities_selling_frame, orient=tk.VERTICAL, command=commodities_selling_text.yview)
        commodities_selling_text['yscrollcommand'] = commodities_selling_scroll.set
        commodities_selling_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        commodities_selling_text.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        commodities_selling_text.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_SELLING))
        commodities_selling_text.configure(state='disabled')
        commodities_selling_frame.grid(row=current_row, column=0, sticky=tk.NSEW)

        commodities_buying_frame:ttk.Frame = ttk.Frame(items_frame)
        commodities_buying_text:TextPlus = TextPlus(commodities_buying_frame, wrap=tk.WORD, height=1, font=FONT_TEXT)
        commodities_buying_scroll:tk.Scrollbar = tk.Scrollbar(commodities_buying_frame, orient=tk.VERTICAL, command=commodities_buying_text.yview)
        commodities_buying_text['yscrollcommand'] = commodities_buying_scroll.set
        commodities_buying_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        commodities_buying_text.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        commodities_buying_text.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_BUYING))
        commodities_buying_text.configure(state='disabled')
        commodities_buying_frame.grid(row=current_row, column=1, sticky=tk.NSEW)

        items_frame.columnconfigure(0, weight=1) # Make the first column fill available space
        items_frame.columnconfigure(1, weight=1) # Make the second column fill available space
        items_frame.rowconfigure(1, weight=1) # Make the materials text fill available space
        items_frame.rowconfigure(3, weight=1) # Make the commodities text fill available space


        self.post_button:ttk.Button = ttk.Button(buttons_frame, text=_("Post to Discord"), command=partial(self._post_to_discord)) # LANG: Button
        self.post_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.post_button.config(state=(tk.NORMAL if self.bgstally.discord.valid_webhook_available(DiscordChannel.FLEETCARRIER_MATERIALS) else tk.DISABLED))


    def _post_to_discord(self):
        """
        Post Fleet Carrier materials list to Discord
        """
        self.post_button.config(state=tk.DISABLED)

        fc:FleetCarrier = self.bgstally.fleet_carrier

        title:str = f"Materials List for Carrier {fc.name} in system: {fc.data['currentStarSystem']}"
        description:str = ""
        materials_selling:str = fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_SELLING)
        materials_buying:str = fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_BUYING)
        commodities_selling:str = fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_SELLING)
        commodities_buying:str = fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_BUYING)

        if materials_selling != "":
            description += "**" + __("Selling Materials:") + f"**\n```css\n{materials_selling}```\n" # LANG: Discord fleet carrier section heading
        if materials_buying != "":
            description += "**" + __("Buying Materials:") + f"**\n```css\n{materials_buying}```\n" # LANG: Discord fleet carrier section heading
        if commodities_selling != "":
            description += "**" + __("Selling Commodities:") + f"**\n```css\n{commodities_selling}```\n" # LANG: Discord fleet carrier section heading
        if commodities_buying != "":
            description += "**" + __("Buying Commodities:") + f"**\n```css\n{commodities_buying}```\n" # LANG: Discord fleet carrier section heading

        fields = []
        fields.append({'name': __("System"), 'value': fc.data['currentStarSystem'], 'inline': True}) # LANG: Discord fleet carrier field heading
        fields.append({'name': __("Docking"), 'value': fc.human_format_dockingaccess(True), 'inline': True}) # LANG: Discord fleet carrier field heading
        fields.append({'name': __("Notorious Access"), 'value': fc.human_format_notorious(True), 'inline': True}) # LANG: Discord fleet carrier field heading

        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)

        self.post_button.after(5000, self._enable_post_button)


    def _enable_post_button(self):
        """
        Re-enable the post to discord button if it should be enabled
        """
        self.post_button.config(state=(tk.NORMAL if self.bgstally.discord.valid_webhook_available(DiscordChannel.FLEETCARRIER_MATERIALS) else tk.DISABLED))
