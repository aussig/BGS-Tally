import tkinter as tk
from functools import partial
from tkinter import ttk

from bgstally.constants import (COLOUR_HEADING_1, COLOUR_WARNING, FONT_HEADING_1, FONT_HEADING_2, FONT_TEXT, CheckStates,
                                DiscordChannel, FleetCarrierItemType)
from bgstally.debug import Debug
from bgstally.fleetcarrier import FleetCarrier
from bgstally.utils import _, __
from bgstally.widgets import TextPlus
from config import config
from thirdparty.colors import *
from thirdparty.Tooltip import ToolTip

class WindowFleetCarrier:
    """
    Handles the Fleet Carrier window
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

        fc: FleetCarrier = self.bgstally.fleet_carrier

        self.toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.toplevel.title(_("{plugin_name} - Carrier {carrier_name} ({carrier_callsign}) in system: {system_name}").format(plugin_name=self.bgstally.plugin_name, carrier_name=fc.name, carrier_callsign=fc.callsign, system_name=fc.data.get('currentStarSystem', "Unknown"))) # LANG: Carrier window title
        self.toplevel.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.toplevel.geometry("800x800")

        frm_container: ttk.Frame = ttk.Frame(self.toplevel)
        frm_container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm_container, text=_("System: {current_system} - Docking: {docking_access} - Notorious Allowed: {notorious}").format(current_system=fc.data.get('currentStarSystem', "Unknown"), docking_access=fc.human_format_dockingaccess(False), notorious=fc.human_format_notorious(False)), font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).pack(anchor=tk.NW) # LANG: Label on carrier window

        if not config.get_bool('capi_fleetcarrier'):
            ttk.Label(frm_container, text=_("Some information cannot be updated. Enable Fleet Carrier CAPI Queries in File -> Settings -> Configuration"), foreground=COLOUR_WARNING).pack(anchor=tk.NW) # LANG: Label on carrier window

        frm_items: ttk.Frame = ttk.Frame(frm_container)
        frm_items.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        frm_buttons: ttk.Frame = ttk.Frame(frm_container)
        frm_buttons.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        current_row = 0

        s: ttk.Style = ttk.Style()
        s.configure('This.TCheckbutton', font=FONT_HEADING_2)

        ttk.Checkbutton(frm_items, text=_("Selling Materials"), style='This.TCheckbutton', variable=self.bgstally.state.FcSellingMaterials, onvalue=CheckStates.STATE_ON, \
                        offvalue=CheckStates.STATE_OFF, command=partial(self.bgstally.state.FcSellingMaterials.set)).grid(row=current_row, column=0, padx=10, sticky=tk.W)

        ttk.Checkbutton(frm_items, text=_("Buying Materials"), style='This.TCheckbutton', variable=self.bgstally.state.FcBuyingMaterials, onvalue=CheckStates.STATE_ON, \
                        offvalue=CheckStates.STATE_OFF, command=partial(self.bgstally.state.FcBuyingMaterials.set)).grid(row=current_row, column=1, padx=10, sticky=tk.W)

        current_row += 1

        frm_materials_selling: ttk.Frame = ttk.Frame(frm_items)
        txt_materials_selling: TextPlus = TextPlus(frm_materials_selling, wrap=tk.WORD, height=1, font=FONT_TEXT)
        sb_materials_selling: tk.Scrollbar = tk.Scrollbar(frm_materials_selling, orient=tk.VERTICAL, command=txt_materials_selling.yview)
        txt_materials_selling['yscrollcommand'] = sb_materials_selling.set
        sb_materials_selling.pack(fill=tk.Y, side=tk.RIGHT)
        txt_materials_selling.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        txt_materials_selling.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_SELLING))
        txt_materials_selling.configure(state='disabled')
        frm_materials_selling.grid(row=current_row, column=0, sticky=tk.NSEW)

        frm_materials_buying: ttk.Frame = ttk.Frame(frm_items)
        txt_materials_buying: TextPlus = TextPlus(frm_materials_buying, wrap=tk.WORD, height=1, font=FONT_TEXT)
        sb_materials_buying: tk.Scrollbar = tk.Scrollbar(frm_materials_buying, orient=tk.VERTICAL, command=txt_materials_buying.yview)
        txt_materials_buying['yscrollcommand'] = sb_materials_buying.set
        sb_materials_buying.pack(fill=tk.Y, side=tk.RIGHT)
        txt_materials_buying.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        txt_materials_buying.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_BUYING))
        txt_materials_buying.configure(state='disabled')
        frm_materials_buying.grid(row=current_row, column=1, sticky=tk.NSEW)

        current_row += 1

        ttk.Checkbutton(frm_items, text=_("Selling Commodities"), style='This.TCheckbutton', variable=self.bgstally.state.FcSellingCommodities, onvalue=CheckStates.STATE_ON, \
                        offvalue=CheckStates.STATE_OFF, command=partial(self.bgstally.state.FcSellingCommodities.set)).grid(row=current_row, column=0, padx=10, sticky=tk.W)

        ttk.Checkbutton(frm_items, text=_("Buying Commodities"), style='This.TCheckbutton', variable=self.bgstally.state.FcBuyingCommodities, onvalue=CheckStates.STATE_ON, \
                        offvalue=CheckStates.STATE_OFF, command=partial(self.bgstally.state.FcBuyingCommodities.set)).grid(row=current_row, column=1, padx=10, sticky=tk.W)

        current_row += 1

        frm_commodities_selling: ttk.Frame = ttk.Frame(frm_items)
        txt_commodities_selling: TextPlus = TextPlus(frm_commodities_selling, wrap=tk.WORD, height=1, font=FONT_TEXT)
        sb_commodities_selling: tk.Scrollbar = tk.Scrollbar(frm_commodities_selling, orient=tk.VERTICAL, command=txt_commodities_selling.yview)
        txt_commodities_selling['yscrollcommand'] = sb_commodities_selling.set
        sb_commodities_selling.pack(fill=tk.Y, side=tk.RIGHT)
        txt_commodities_selling.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        txt_commodities_selling.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_SELLING))
        txt_commodities_selling.configure(state='disabled')
        frm_commodities_selling.grid(row=current_row, column=0, sticky=tk.NSEW)

        frm_commodities_buying: ttk.Frame = ttk.Frame(frm_items)
        txt_commodities_buying: TextPlus = TextPlus(frm_commodities_buying, wrap=tk.WORD, height=1, font=FONT_TEXT)
        sb_commodities_buying: tk.Scrollbar = tk.Scrollbar(frm_commodities_buying, orient=tk.VERTICAL, command=txt_commodities_buying.yview)
        txt_commodities_buying['yscrollcommand'] = sb_commodities_buying.set
        sb_commodities_buying.pack(fill=tk.Y, side=tk.RIGHT)
        txt_commodities_buying.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        txt_commodities_buying.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_BUYING))
        txt_commodities_buying.configure(state='disabled')
        frm_commodities_buying.grid(row=current_row, column=1, sticky=tk.NSEW)

        current_row += 1
        ttk.Checkbutton(frm_items, text=_("Cargo"), style='This.TCheckbutton', variable=self.bgstally.state.FcCargo, onvalue=CheckStates.STATE_ON, \
                        offvalue=CheckStates.STATE_OFF, command=partial(self.bgstally.state.FcCargo.set)).grid(row=current_row, column=0, padx=10, sticky=tk.W)

        ttk.Checkbutton(frm_items, text=_("Locker"), style='This.TCheckbutton', variable=self.bgstally.state.FcLocker, onvalue=CheckStates.STATE_ON, \
                        offvalue=CheckStates.STATE_OFF, command=partial(self.bgstally.state.FcLocker.set)).grid(row=current_row, column=1, padx=10, sticky=tk.W)


        current_row += 1

        frm_cargo: ttk.Frame = ttk.Frame(frm_items)
        txt_cargo: TextPlus = TextPlus(frm_cargo, wrap=tk.WORD, height=1, font=FONT_TEXT)
        sb_cargo: tk.Scrollbar = tk.Scrollbar(frm_cargo, orient=tk.VERTICAL, command=txt_cargo.yview)
        txt_cargo['yscrollcommand'] = sb_cargo.set
        sb_cargo.pack(fill=tk.Y, side=tk.RIGHT)
        txt_cargo.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        txt_cargo.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.CARGO))
        txt_cargo.configure(state='disabled')
        frm_cargo.grid(row=current_row, column=0, sticky=tk.NSEW)

        frm_locker: ttk.Frame = ttk.Frame(frm_items)
        txt_locker: TextPlus = TextPlus(frm_locker, wrap=tk.WORD, height=1, font=FONT_TEXT)
        sb_locker: tk.Scrollbar = tk.Scrollbar(frm_locker, orient=tk.VERTICAL, command=txt_locker.yview)
        txt_locker['yscrollcommand'] = sb_locker.set
        sb_locker.pack(fill=tk.Y, side=tk.RIGHT)
        txt_locker.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        txt_locker.insert(tk.INSERT, fc.get_items_plaintext(FleetCarrierItemType.LOCKER))
        txt_locker.configure(state='disabled')
        frm_locker.grid(row=current_row, column=1, sticky=tk.NSEW)

        frm_items.columnconfigure(0, weight=1) # Make the first column fill available space
        frm_items.columnconfigure(1, weight=1) # Make the second column fill available space
        frm_items.rowconfigure(1, weight=1) # Make the materials text fill available space
        frm_items.rowconfigure(3, weight=1) # Make the commodities text fill available space
        frm_items.rowconfigure(5, weight=1) # Make the cargo/locker text fill available space

        self.btn_copy_to_clipboard: tk.Button = tk.Button(frm_buttons, text=_("Copy to Clipboard"), command=partial(self._copy_to_clipboard, frm_container)) # LANG: Button label
        self.btn_copy_to_clipboard.pack(side=tk.LEFT, padx=5, pady=5)

        self.btn_post_to_discord: tk.Button = tk.Button(frm_buttons, text=_("Post to Discord"), command=partial(self._post_to_discord)) # LANG: Button
        self.btn_post_to_discord.pack(side=tk.RIGHT, padx=5, pady=5)
        if not self._discord_button_available():
            ToolTip(self.btn_post_to_discord, text=_("Both the 'Post to Discord as' field and a Discord webhook{CR}must be configured in the settings to allow posting to Discord").format(CR="\n")) # LANG: Post to Discord button tooltip

        self._enable_post_button()



    def _post_type_selected(self, post_types: dict, value: str):
        """The user has changed the dropdown to choose the type of data to post
        """
        k: str = next(k for k, v in post_types.items() if v == value)
        self.bgstally.state.DiscordFleetCarrier.set(k)


    def _post_to_discord(self):
        """
        Post Fleet Carrier materials list to Discord
        """
        self.btn_post_to_discord.config(state=tk.DISABLED)

        fc: FleetCarrier = self.bgstally.fleet_carrier

        title: str = __("Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=fc.name) # LANG: Discord fleet carrier title
        description: str = self._get_as_text(fc, True)

        fields: list = []
        fields.append({'name': __("System", lang=self.bgstally.state.discord_lang), 'value': fc.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord fleet carrier field heading
        fields.append({'name': __("Docking", lang=self.bgstally.state.discord_lang), 'value': fc.human_format_dockingaccess(True), 'inline': True}) # LANG: Discord fleet carrier field heading
        fields.append({'name': __("Notorious Access", lang=self.bgstally.state.discord_lang), 'value': fc.human_format_notorious(True), 'inline': True}) # LANG: Discord fleet carrier field heading

        self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)

        self.btn_post_to_discord.after(5000, self._enable_post_button)


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
            text += "**" + __("Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=fc.name) + "**\n\n" # LANG: Discord fleet carrier title

        materials_selling: str = fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_SELLING)
        materials_buying: str = fc.get_items_plaintext(FleetCarrierItemType.MATERIALS_BUYING)
        commodities_selling: str = fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_SELLING)
        commodities_buying: str = fc.get_items_plaintext(FleetCarrierItemType.COMMODITIES_BUYING)
        cargo: str = fc.get_items_plaintext(FleetCarrierItemType.CARGO)
        locker: str = fc.get_items_plaintext(FleetCarrierItemType.LOCKER)

        if self.bgstally.state.FcSellingMaterials.get() == CheckStates.STATE_ON and materials_selling != "":
            text += "**" + __("Selling Materials:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{materials_selling}```\n" # LANG: Discord fleet carrier section heading
        if self.bgstally.state.FcBuyingMaterials.get() == CheckStates.STATE_ON and materials_buying != "":
            text += "**" + __("Buying Materials:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{materials_buying}```\n" # LANG: Discord fleet carrier section heading
        if self.bgstally.state.FcSellingCommodities.get() == CheckStates.STATE_ON  and commodities_selling != "":
            text += "**" + __("Selling Commodities:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{commodities_selling}```\n" # LANG: Discord fleet carrier section heading
        if self.bgstally.state.FcBuyingCommodities.get() == CheckStates.STATE_ON  and commodities_buying != "":
            text += "**" + __("Buying Commodities:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{commodities_buying}```\n" # LANG: Discord fleet carrier section heading
        if self.bgstally.state.FcCargo.get() == CheckStates.STATE_ON  and cargo != "":
            text += "**" + __("Cargo:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{cargo}```\n" # LANG: Discord fleet carrier section heading
        if self.bgstally.state.FcLocker.get() == CheckStates.STATE_ON  and locker != "":
            text += "**" + __("Locker:", lang=self.bgstally.state.discord_lang) + f"**\n```css\n{locker}```\n" # LANG: Discord fleet carrier section heading

        if not short:
            text += "**" + __("System", lang=self.bgstally.state.discord_lang) + "**: " + fc.data.get('currentStarSystem', "Unknown") + "\n" # LANG: Discord fleet carrier discord post
            text += "**" + __("Docking", lang=self.bgstally.state.discord_lang) + "**: " + fc.human_format_dockingaccess(True) + "\n" # LANG: Discord fleet carrier discord post
            text += "**" + __("Notorious Access", lang=self.bgstally.state.discord_lang) + "**: " + fc.human_format_notorious(True) # LANG: Discord fleet carrier discord post

        return text


    def _enable_post_button(self):
        """
        Re-enable the post to discord button if it should be enabled
        """
        self.btn_post_to_discord.config(state=(tk.NORMAL if self._discord_button_available() else tk.DISABLED))


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
