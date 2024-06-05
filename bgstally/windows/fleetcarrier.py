import tkinter as tk
from functools import partial
from tkinter import ttk

from bgstally.constants import COLOUR_HEADING_1, FONT_HEADING_1, FONT_HEADING_2, FONT_TEXT, DiscordChannel, FleetCarrierItemType
from bgstally.debug import Debug
from bgstally.fleetcarrier import FleetCarrier
from bgstally.utils import _, __
from bgstally.widgets import TextPlus
from config import config
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
        self.toplevel.title(_("{plugin_name} - Carrier {carrier_name} ({carrier_callsign}) in system: {system_name}").format(plugin_name=self.bgstally.plugin_name, carrier_name=fc.name, carrier_callsign=fc.callsign, system_name=fc.data.get('currentStarSystem', "Unknown"))) # LANG: Carrier window title
        self.toplevel.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.toplevel.geometry("800x800")

        container_frame:ttk.Frame = ttk.Frame(self.toplevel)
        container_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container_frame, text=_("System: {current_system} - Docking: {docking_access} - Notorious Allowed: {notorious}").format(current_system=fc.data.get('currentStarSystem', "Unknown"), docking_access=fc.human_format_dockingaccess(False), notorious=fc.human_format_notorious(False)), font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).pack(anchor=tk.NW) # LANG: Label on carrier window

        if not config.get_bool('capi_fleetcarrier'):
            ttk.Label(container_frame, text=_("Some information cannot be updated. Enable Fleet Carrier CAPI Queries in File -> Settings -> Configuration"), foreground='#f00').pack(anchor=tk.NW) # LANG: Label on carrier window

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

        self.copy_to_clipboard_button: tk.Button = tk.Button(buttons_frame, text=_("Copy to Clipboard"), command=partial(self._copy_to_clipboard, container_frame)) # LANG: Button label
        self.copy_to_clipboard_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.post_button: tk.Button = tk.Button(buttons_frame, text=_("Post to Discord"), command=partial(self._post_to_discord)) # LANG: Button
        self.post_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self._enable_post_button()


    def _post_to_discord(self):
        """
        Post Fleet Carrier materials list to Discord
        """
        self.post_button.config(state=tk.DISABLED)

        fc: FleetCarrier = self.bgstally.fleet_carrier

        title: str = __("Materials List for Carrier {carrier_name} in system: {system}", lang=self.bgstally.state.discord_lang).format(carrier_name=fc.name, system=fc.data.get('currentStarSystem', "Unknown")) # LANG: Discord fleet carrier title
        description: str = self._get_as_text(fc, True)

        fields: list = []
        fields.append({'name': __("System", lang=self.bgstally.state.discord_lang), 'value': fc.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord fleet carrier field heading
        fields.append({'name': __("Docking", lang=self.bgstally.state.discord_lang), 'value': fc.human_format_dockingaccess(True), 'inline': True}) # LANG: Discord fleet carrier field heading
        fields.append({'name': __("Notorious Access", lang=self.bgstally.state.discord_lang), 'value': fc.human_format_notorious(True), 'inline': True}) # LANG: Discord fleet carrier field heading

        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)

        self.post_button.after(5000, self._enable_post_button)


    def _get_as_text(self, fc: FleetCarrier, short: bool = False) -> str:
        """Get a string containing the fleet carrier information

        Args:
            fc (FleetCarrier): The FleetCarrier object
            short (bool): If true, return a short report excluding the carrier name, location and docking access

        Returns:
            str: The fleet carrier information
        """
        text: str = ""

        if not short:
            text += "**" + __("Materials List for Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=fc.name) + "**\n\n" # LANG: Discord fleet carrier title

        materials_selling: str = fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_SELLING)
        materials_buying: str = fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_BUYING)
        commodities_selling: str = fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_SELLING)
        commodities_buying: str = fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_BUYING)

        if materials_selling != "":
            text += "**" + __("Selling Materials:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{materials_selling}```\n" # LANG: Discord fleet carrier section heading
        if materials_buying != "":
            text += "**" + __("Buying Materials:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{materials_buying}```\n" # LANG: Discord fleet carrier section heading
        if commodities_selling != "":
            text += "**" + __("Selling Commodities:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{commodities_selling}```\n" # LANG: Discord fleet carrier section heading
        if commodities_buying != "":
            text += "**" + __("Buying Commodities:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{commodities_buying}```\n" # LANG: Discord fleet carrier section heading

        if not short:
            text += "**" + __("System", lang=self.bgstally.state.discord_lang) + "**: " + fc.data.get('currentStarSystem', "Unknown") + "\n" # LANG: Discord fleet carrier discord post
            text += "**" + __("Docking", lang=self.bgstally.state.discord_lang) + "**: " + fc.human_format_dockingaccess(True) + "\n" # LANG: Discord fleet carrier discord post
            text += "**" + __("Notorious Access", lang=self.bgstally.state.discord_lang) + "**: " + fc.human_format_notorious(True) # LANG: Discord fleet carrier discord post

        return text


    def _enable_post_button(self):
        """
        Re-enable the post to discord button if it should be enabled
        """
        self.post_button.config(state=(tk.NORMAL if self._discord_button_available() else tk.DISABLED))


    def _discord_button_available(self) -> bool:
        """
        Return true if the 'Post to Discord' button should be available
        """
        return (self.bgstally.discord.valid_webhook_available(DiscordChannel.FLEETCARRIER_MATERIALS)
                and self.bgstally.state.DiscordUsername.get() != "")


    def _copy_to_clipboard(self, frm_container: tk.Frame):
        """Get text version of the fleetcarrier information and put it in the Copy buffer

        Args:
            frm_container (tk.Frame): The parent tk Frame
        """
        fc: FleetCarrier = self.bgstally.fleet_carrier
        text: str = self._get_as_text(fc, False)

        frm_container.clipboard_clear()
        frm_container.clipboard_append(text)
        frm_container.update()
