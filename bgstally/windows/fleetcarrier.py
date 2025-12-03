import tkinter as tk
from functools import partial
from tkinter import ttk

#from bgstally.bgstally import BGSTally
from bgstally.constants import DATETIME_FORMAT_CARRIER, FONT_SMALL, COLOUR_WARNING, DiscordChannel, DiscordFleetCarrier
from bgstally.fleetcarrier import FleetCarrier
from bgstally.debug import Debug
from bgstally.utils import _, __, hfplus, str_truncate, catch_exceptions
from bgstally.widgets import TreeviewPlus, AutoCompleter, Placeholder
from config import config # type: ignore

from thirdparty.colors import *
from thirdparty.Tooltip import ToolTip
from thirdparty.ScrollableNotebook import ScrollableNotebook

class WindowFleetCarrier:
    """
    Handles the Fleet Carrier window.
    The window shows an overview of current carrier status and tabs for cargo, materials etc.
    Tabs have a summary and typically a table of relevant items.
    Buttons are provided to copy information to the clipboard or post directly to discord.
    """

    def __init__(self, bgstally) -> None:
        self.bgstally:BGSTally = bgstally # type: ignore
        self.window:tk.Toplevel|None = None
        self.frame:ttk.Frame
        self.itineraryfr:ttk.Frame
        self.scale:float = 1.0

        self.tabs:dict = {
            'Summary': {
                'cols': {
                    'service': {'title': 'Service', 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 225, 'locName': _('Service')}, # LANG: Services summary tab
                    'enabled': {'title': 'Enabled', 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 85, 'locName': _('Enabled')}, # LANG: Services summary tab
                    'status': {'title': 'Status', 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 100, 'locName': _('Status')}, # LANG: Services summary tab
                    'name': {'title': 'Crew Member', 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 175, 'locName': _('Crew Member')}, # LANG: Services summary tab
                    'taxation': {'title': 'Tax Rate', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 75, 'locName': _('Tax Rate')}, # LANG: Services summary tab
                    'salary' : {'title': 'Salary', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 85, 'locName': _('Salary')}, # LANG: Services summary tab
                    'hiringPrice': {'title': 'Hiring Cost', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 100, 'locName': _('Hiring Cost')}, # LANG: Services summary tab
                },
                'names': {'vistagenomics': _('Vista Genomics'), # LANG: Service name
                          'pioneersupplies': _('Pioneer Supplies'), # LANG: Service name
                          'voucherredemption': _('Redemption'), # LANG: Service name
                },
                'ignore': ['stationmenu', 'carrierfuel', 'commodities', 'carriermanagement', 'dock',
                           'crewlounge', 'engineer', 'socialspace', 'contacts', 'registeringcolonisation',
                           'livery', 'lastEdit', 'faction', 'gender'],
                "func": self._summary
            },
            'Cargo': {
                'cols': {
                    'locName': {'title': 'Commodity', 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250, 'discordWidth':20, 'locName': _('Commodity')}, # LANG: Cargo tab
                    'category': {'title': 'Category', 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 150, 'discordWidth':14, 'locName': _('Category')}, # LANG: Cargo tab
                    'stock': {'title': 'Stock', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'discordWidth':6, 'locName': _('Stock')}, # LANG: Cargo tab
                    'buy': {'title': 'Buying', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'discordWidth':6, 'locName': _('Buying')}, # LANG: Cargo tab
                    'sell': {'title': 'Selling', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'discordWidth':7, 'locName': _('Selling')}, # LANG: Cargo tab
                    'price': {'title': 'Price', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'discordWidth':7, 'locName': _('Price')}, # LANG: Cargo tab
                    'stolen': {'title': 'Stolen', 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'locName': _('Stolen')}, # LANG: Cargo tab
                    'mission': {'title': 'Mission', 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'locName': _('Mission')} # LANG: Cargo tab
                },
                "func": self._cargo,
                "buttons": self._cargo_buttons,
            },
            'Locker': {
                'cols': {
                    'locName': {'title': 'Material', 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250, 'discordWidth':20, 'locName': _('Material')}, # LANG: Locker tab
                    'category': {'title': 'Category', 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 150, 'discordWidth':8, 'locName': _('Category')}, # LANG: Locker tab
                    'stock': {'title': 'Stock', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'discordWidth':5, 'locName': _('Stock')}, # LANG: Locker tab
                    'buy': {'title': 'Buying', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'discordWidth':6, 'locName': _('Buying')}, # LANG: Locker tab
                    'sell': {'title': 'Selling', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'discordWidth':7, 'locName': _('Selling')}, # LANG: Locker tab
                    'price': {'title': 'Price', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'discordWidth':5, 'locName': _('Price')}, # LANG: Locker tab
                    'mission': {'title': 'Mission', 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'locName': _('Mission')} # LANG: Locker tab
                },
                "func": self._locker,
                'buttons': self._locker_buttons,
            },
            'Itinerary': {
                'cols': {
                    'starsystem': {'title': 'Location', 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250, 'locName': _('Location')}, # LANG: Itinerary tab
                    'visitDurationSeconds': {'title': 'Duration', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 150, 'locName': _('Duration')}, # LANG: Itinerary tab
                    'arrivalTime': {'title': 'Arrived', 'sort': 'datetime', 'align': tk.E, 'stretch': tk.NO, 'width': 150, 'locName': _('Arrived')}, # LANG: Itinerary tab
                    'departureTime': {'title': 'Departed', 'sort': 'datetime', 'align': tk.E, 'stretch': tk.NO, 'width': 150, 'locName': _('Departed')}, # LANG: Itinerary tab
                    'state': {'title': 'Status', 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 100, 'locName': _('Status')}, # LANG: Itinerary tab
                },
                'route_cols': {
                    'starsystem': {'title': 'Location', 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250, 'locName': _('Location')}, # LANG: Itinerary tab
                    'distance': {'title': 'Distance', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 100, 'locName': _('Distance')}, # LANG: Itinerary tab
                    'distance_to_destination': {'title': 'Remaining Distance', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 100, 'locName': _('Remaining')}, # LANG: Itinerary tab
                    'fuel_used': {'title': 'Arrived', 'sort': 'datetime', 'align': tk.E, 'stretch': tk.NO, 'width': 150, 'locName': _('Fuel Used')}, # LANG: Itinerary tab
                    'fuel_in_depot': {'title': 'Fuel In Depot', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 150, 'locName': _('Fuel In Depot')}, # LANG: Itinerary tab
                    'state': {'title': 'Status', 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 100, 'locName': _('Status')}, # LANG: Itinerary tab
                },
                'func': self._itinerary,
                'buttons': self._routing_buttons,
            },
            'Shipyard': {
                'cols': {
                    'name': {'title': 'Name', 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 200, 'locName': _('Name')}, # LANG: Shipyard tab
                    'type': {'title': 'Type', 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 200, 'locName': _('Type')}, # LANG: Shipyard tab
                    #{'title': 'Location', 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 175, 'locName': _('Location')}, # LANG: Shipyard tab
                    'value': {'title': 'Value', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 90, 'locName': _('Value')}, # LANG: Shipyard tab
                    'hot': {'title': 'Hot', 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70, 'locName': _('Hot')}, # LANG: Shipyard tab
                    'transferTime': {'title': 'Transfer Time', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 175, 'locName': _('Transfer Time')}, # LANG: Shipyard tab
                    'transferPrice': {'title': 'Transfer Cost', 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 125, 'locName': _('Transfer Cost')}, # LANG: Shipyard tab
                },
                'func': self._shipyard
            },
        }


    @catch_exceptions
    def show(self) -> None:
        """ Show our window """
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            return

        self.scale = config.get_int('ui_scale') / 100.00
        self.window = tk.Toplevel(self.bgstally.ui.frame)
        self.window.title(_("{plugin_name} - Carrier {carrier_name}").format(plugin_name=self.bgstally.plugin_name, carrier_name=self.bgstally.fleet_carrier.overview.get('name'))) # LANG: Carrier window title
        self.window.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.window.geometry(f"{int(850*self.scale)}x{int(550*self.scale)}")

        self.frame = ttk.Frame(self.window)
        if not config.get_bool('capi_fleetcarrier'):
            ttk.Label(self.frame, text=_("Some information cannot be updated. Enable Fleet Carrier CAPI Queries in File -> Settings -> Configuration"), foreground=COLOUR_WARNING).pack(anchor=tk.NW) # LANG: Label on carrier window

        self.update_display()
        self.frame.pack(fill=tk.BOTH, expand=True)


    def update_display(self) -> None:
        """ Update the Fleet Carrier window contents """
        if self.window == None or not self.window.winfo_exists(): return

        # Clear existing contents
        for w in self.frame.winfo_children(): w.destroy()

        self._show_overview(self.bgstally.fleet_carrier, self.frame)
        self._create_tabs(self.bgstally.fleet_carrier, self.frame)


    def _show_overview(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        """ Show the Fleet Carrier overview tab """
        summ:ttk.Frame = ttk.Frame(frame)
        summ.pack(fill=tk.X)
        self._create_columns(fc.get_overview(), 3, summ)


    def _create_tabs(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        """ Create and populate the Fleet Carrier tabs """

        style:ttk.Style = ttk.Style()
        style.configure("White.TNotebook.Tab", font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), padding=[10, 5], background='green')
        tabbar:ScrollableNotebook = ScrollableNotebook(frame, wheelscroll=True, tabmenu=False, style='White.TNotebook')
        tabbar.pack(fill=tk.X, padx=5, pady=5)

        for k, v in self.tabs.items():
            fr:ttk.Frame = ttk.Frame(tabbar, relief=tk.FLAT)
            fr.pack(fill=tk.BOTH, expand=1)
            tabbar.add(fr, text=_(k))
            if v.get('buttons', None) != None:
                v['buttons'](fc, fr)
            v['func'](fc, v, fr)


    def _summary(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        summary:dict = fc.get_summary()

        sections:dict = {'finances': _('Finances'), # LANG: Summary headings
                         'costs': _('Running Costs'), # LANG: Summary headings
                         'capacity': _('Capacity')} # LANG: Summary headings

        fr:ttk.Frame = ttk.Frame(frame, relief=tk.FLAT, style="White.TFrame")
        fr.pack(fill=tk.BOTH, expand=1)
        for k, v in sections.items():
            if summary.get(k, None) != None:
                lbl = ttk.Label(fr, text=v.upper(), font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), background='white')
                lbl.pack(padx=5, pady=(5, 0), fill=tk.X)
                style:ttk.Style = ttk.Style()
                style.configure("White.TFrame", background='white')
                summ:ttk.Frame = ttk.Frame(fr, style="White.TFrame")
                summ.configure(padding=10)
                summ.pack(fill=tk.X)
                self._create_columns(summary[k], 3 if k == 'capacity' else 4, summ, bg='white')
                if k != 'capacity':
                    separator:ttk.Separator = ttk.Separator(fr, orient=tk.HORIZONTAL)
                    separator.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

        services:dict = fc.get_services()

        table:TreeviewPlus = self._create_table(which['cols'], fr)
        for s, v in sorted(services.get('crew', {}).items()):
            if s in which['ignore']: continue
            row:list = []
            for c in which['cols'].keys():
                if c in which['ignore']: continue
                val:str = ''
                match c:
                    case 'service': val = s.title() if s not in which['names'].keys() else which['names'][s]
                    case _: val = hfplus(v.get(c, ""))
                row.append(val)
            table.insert("", 'end', values=row)


    def _cargo(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Create and display the Cargo tab """
        cargo:dict = fc.get_cargo()

        if cargo.get('overview', None) != None:
            self._overview(cargo['overview'], 4, frame, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for name, i in cargo['inventory'].items():
            line:list = []
            for c in which['cols'].keys():
                val:str = ""
                match c:
                    case "buy" if i.get("price", 0) > 0 and i.get("outstanding", 0) > 0: val = i.get("outstanding")
                    case "sell" if i.get("price", 0) > 0 and i.get("stock", 0) > 0 and i.get('buyTotal') == 0: val = i.get("stock")
                    case _: val = i.get(c, " ")
                if i.get('stock', 0) > 0 or i.get('outstanding', 0) > 0:
                    line.append(hfplus(val))
            if line != []:
                table.insert("", 'end', values=line, iid=i.get('locName'))


    def _locker(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Create and display the Locker tab """
        locker:dict = fc.get_locker()

        if locker.get('overview', None) != None:
            self._overview(locker['overview'], 4, frame, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for cat, i in locker.get('inventory', {}).items():
            row:list = []
            for c in which['cols'].keys():
                val:str = ""
                match c:
                    case "buy" if i.get("price", 0) > 0 and i.get("outstanding", 0) > 0: val = i.get("outstanding")
                    case "sell" if i.get("price", 0) > 0 and i.get("stock", 0) > 0: val = i.get("stock")
                    case _: val = i.get(c, " ")
                if i.get('stock', 0) > 0 or i.get('outstanding', 0) > 0:
                    row.append(hfplus(val))
            if row != []:
                table.insert("", 'end', values=row, iid=i.get('locName'))


    def _itinerary(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Create and display the Itinerary tab """
        ifr:ttk.Frame = ttk.Frame(frame)
        ifr.pack(fill=tk.BOTH, expand=True)
        self.itineraryfr = ifr

        itinerary:dict = fc.get_itinerary()

        if itinerary.get('overview', None) != None:
            self._overview(itinerary['overview'], 4, ifr, bg='white')

        if itinerary.get('route', []) != []:
            rf:ttk.Frame = ttk.Frame(ifr)
            rf.pack(fill=tk.X, side=tk.TOP)
            rt:TreeviewPlus = self._create_table(which['route_cols'], rf)
            for jump in itinerary.get('route', []):
                row:list = []
                for c in self.tabs['Itinerary']['route_cols'].keys():
                    row.append(hfplus(jump.get(c)))
                rt.insert("", 'end', values=row)
            rt.configure(height=min(len(itinerary.get('route', [])), 5))

        it:ttk.Frame = ttk.Frame(ifr)
        it.pack(fill=tk.X, side=tk.TOP)
        table:TreeviewPlus = self._create_table(which['cols'], it)
        for jump in itinerary.get('completed', []):
            row:list = []
            for c in which['cols'].keys():
                row.append(hfplus(jump.get(c)))
            table.insert("", 'end', values=row)
        table.pack(fill="both", expand=True)


    def _shipyard(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Create and display the Itinerary tab """
        shipyard:dict = fc.get_shipyard()

        if shipyard.get('overview', None) != None:
            self._overview(shipyard['overview'], 10, frame, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for ship in shipyard.get('ships', []):
            if ship.get('location')[0] != 'Carrier': continue # Only show ships stored at the carrier
            row:list = []
            for c in which['cols'].keys():
                row.append(hfplus(ship.get(c)))
            table.insert("", 'end', values=row)


    def _overview(self, data:dict, maxcols:int, frame:ttk.Frame, bg:str = 'None') -> None:
        """ Create and display a standard Overview section within a tab """
        style:ttk.Style = ttk.Style()
        style.configure("White.TFrame", background='white')
        ovf:ttk.Frame = ttk.Frame(frame, style="White.TFrame")
        ovf.configure(padding=10)
        ovf.pack(fill=tk.X)
        self._create_columns(data, maxcols, ovf, bg)


    def _create_columns(self, data:dict, maxcols:int, frame:ttk.Frame, bg:str = 'None') -> None:
        ''' Create grid of title/value pairs in columns and rows '''
        row:int = 0; col = 0
        lbl:ttk.Label

        for k, v in data.items():
            if bg != 'None':
                lbl = ttk.Label(frame, text=_(k), font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), background=bg)
            else:
                lbl = ttk.Label(frame, text=_(k), font=(FONT_SMALL[0], FONT_SMALL[1], "bold"))
            lbl.grid(row=row, column=col, padx=20, pady=5, sticky=tk.W)
            txt:str = hfplus(v)
            if bg != 'None':
                lbl = ttk.Label(frame, text=txt, font=FONT_SMALL, background=bg)
            else:
                lbl = ttk.Label(frame, text=txt, font=FONT_SMALL)
            lbl.grid(row=row, column=col+1, padx=(0,10), pady=5, sticky=tk.W)
            col += 2
            if col >= maxcols*2:
                col = 0
                row += 1


    def _cargo_buttons(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        self._discord_buttons('cargo', frame)
    def _locker_buttons(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        self._discord_buttons('locker', frame)
    def _discord_buttons(self, which:str, frame:ttk.Frame) -> None:
        """ Create discord buttons for cargo or locker as appropriate """

        state:tk.StringVar = self.bgstally.state.FcCargo if which == 'Cargo' else self.bgstally.state.FcLocker

        # Internal helper functions.
        def _ctc(which:str, type:str|tk.StringVar) -> None:
            frame.clipboard_clear()
            frame.clipboard_append(self._get_as_text(which, type, False))

        def _post(which:str, type:str|tk.StringVar, btn:ttk.Button) -> None:
            btn.config(state=tk.DISABLED)
            output:str = self._get_as_text(which, type, True)

            while len(output) > 1990:
                split_at:int = output.rfind('\n', 0, 1900)
                part:str = output[0:split_at]
                self.bgstally.discord.post_plaintext(part, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)
                output = output[split_at+1:]
            self.bgstally.discord.post_plaintext(output, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)
            btn.after(5000, _enable_post, btn)

        def _discord_available() -> bool:
            return (self.bgstally.discord.valid_webhook_available(DiscordChannel.FLEETCARRIER_MATERIALS)
                    and self.bgstally.state.DiscordUsername.get() != "")

        def _enable_post(btn:ttk.Button) -> None:
            btn.config(state=(tk.NORMAL if _discord_available() else tk.DISABLED))

        def _post_type_selected(value:tk.StringVar) -> None:
            state.set(value.get())

        bar:ttk.Frame = ttk.Frame(frame)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        post_types:dict = {_("Buying") : DiscordFleetCarrier.BUYING, # LANG: Dropdown menu on activity window
                            _("Selling") : DiscordFleetCarrier.SELLING, # LANG: Dropdown menu on activity window
                            _("Both") : DiscordFleetCarrier.BOTH, # LANG: Dropdown menu on activity window
                            _("All") : DiscordFleetCarrier.ALL} # LANG: Dropdown menu on activity window

        strv:tk.StringVar = tk.StringVar(value=state.get())
        menuv:ttk.OptionMenu = ttk.OptionMenu(bar, strv, strv.get(), *post_types.keys(),
                                              command=lambda val: _post_type_selected(val),
                                              direction='above')

        cbtn:ttk.Button = ttk.Button(bar, text=_("Copy to Clipboard"), command=partial(_ctc, which, strv)) # LANG: Button label
        cbtn.pack(side=tk.LEFT, padx=5, pady=5)
        dbtn = ttk.Button(bar, text=_("Post to Discord"), # LANG: Button label
                                    state=(tk.NORMAL if _discord_available() else tk.DISABLED))
        dbtn.configure(command=partial(_post, which, strv, dbtn))
        dbtn.pack(side=tk.RIGHT, padx=5, pady=5)
        if not _discord_available():
            ToolTip(dbtn, text=_("Both the 'Post to Discord as' field and a Discord webhook{CR}must be configured in the settings to allow posting to Discord").format(CR="\n")) # LANG: Post to Discord button tooltip
        menuv.pack(side=tk.RIGHT, pady=5)


    def _routing_buttons(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        """ Create itinerary buttons for Spansh fleet carrier router """
        # Internal helper functions.
        def _route(dest:ttk.Entry|Placeholder) -> None:
            Debug.logger.debug(f"Creating route")
            fc.spansh_route(dest.get())
            Debug.logger.debug(f"Updating route")
            for w in self.itineraryfr.winfo_children():
                w.destroy()
            self._itinerary(fc, self.tabs['Itinerary'], self.itineraryfr)
            clear.config(state=tk.NORMAL)

        def _clear() -> None:
            fc.clear_route()
            for w in self.itineraryfr.winfo_children():
                w.destroy()
            self._itinerary(fc, self.tabs['Itinerary'], self.itineraryfr)
            dest.delete(0, tk.END)
            clear.config(state=tk.DISABLED)
            calc.config(state=tk.NORMAL)

        bar:tk.Frame = tk.Frame(frame)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        # @TODO: Add scheduled time selection, copy to clipboard, and post to discord
        #minutes = ttk.Spinbox(bar, from_=0, to=60, width=3)
        #minutes.pack(side=tk.RIGHT)
        #ttk.Label(bar, text=":").pack(side=tk.RIGHT)
        #hours = ttk.Spinbox(bar, from_=0, to=24, width=3)
        #hours.pack(side=tk.RIGHT, padx=5)
        #strv:tk.StringVar = tk.StringVar(value='January')
        #month:ttk.OptionMenu = ttk.OptionMenu(bar, strv, strv.get(), *[_('January'), _('February'), _('March'), _('April'), _('May'), _('June'), _('July'), _('August'), _('September'), _('October'), _('November'), _('December')],
        #                                      command=lambda val: _post_type_selected(which, val),
        #                                      direction='above')
        #month.pack(side=tk.RIGHT)
        #day = ttk.Spinbox(bar, from_=0, to=31, width=3)
        #day.pack(side=tk.RIGHT)
        #ttk.Label(bar, text=_("Scheduled for")).pack(side=tk.RIGHT) # LANG: Label on itinerary window


        itinerary:dict = fc.get_itinerary()
        #dest:ttk.Entry = ttk.Entry(bar, width=30)
        #ph:str = _("Destination") if itinerary.get('route', []) == [] else itinerary['route'][-1].get('name') # LANG: Entry placeholder
        pho:Placeholder = Placeholder(bar, _("Destination"), width=30)
        dest:AutoCompleter = AutoCompleter(self.bgstally, bar, _("Destination"), width=30)
        calc:ttk.Button = ttk.Button(bar, text=_("Calculate"), command=partial(_route, dest)) # LANG: Button label

        lbl:ttk.Label = ttk.Label(bar, text=_("Plot Route"))

        calc.config(state=tk.DISABLED if itinerary.get('route', []) != [] else tk.NORMAL)

        clear:ttk.Button = ttk.Button(bar, text=_("Clear"), command=partial(_clear)) # LANG: Button label
        clear.config(state=tk.DISABLED if itinerary.get('route', []) == [] else tk.NORMAL)

        # At the bottom as order of definition and order of display are different
        calc.pack(side=tk.RIGHT, padx=5, pady=5)
        dest.pack(side=tk.RIGHT, padx=5, pady=5)
        lbl.pack(side=tk.RIGHT, padx=5, pady=5)
        clear.pack(side=tk.RIGHT, padx=5, pady=5)

        return


    @catch_exceptions
    def _create_table(self, cols:dict, frame:ttk.Frame) -> TreeviewPlus:
        """ Create a treeview table with headings and columns """
        style = ttk.Style()
        style.configure("My.Treeview.Heading", font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), background='lightgrey')

        # On click copy the first column to the clipboard
        def _selected(values, column, tr:TreeviewPlus, iid:str) -> None:
            #Debug.logger.debug(f"Values: {values}, Column: {column}, iid: {iid}")
            frame.clipboard_clear()
            frame.clipboard_append(values[0])

        table:TreeviewPlus = TreeviewPlus(frame, height=100, columns=[d['title'] for d in cols.values()], show="headings", callback=_selected, datetime_format=DATETIME_FORMAT_CARRIER, style="My.Treeview")
        sb:ttk.Scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=table.yview)
        sb.pack(fill=tk.Y, side=tk.RIGHT)
        table.configure(yscrollcommand=sb.set)
        table.pack(fill=tk.X, expand=1)
        for v in cols.values():
            table.heading(v['title'], text=v['locName'].title(), anchor=v['align'], sort_by=v['sort'])
            table.column(v['title'], anchor=v['align'], stretch=v['stretch'], width=v['width'])

        return table


    @catch_exceptions
    def _get_as_text(self, which:str, type:str|tk.StringVar, discord:bool = False) -> str:
        """ Get the cargo or locker as text for pasting or posting to Discord """
        fc: FleetCarrier = self.bgstally.fleet_carrier
        l:str|None = self.bgstally.state.discord_lang if discord else ""
        tab:dict = self.tabs[which]
        if isinstance(type, tk.StringVar): type = type.get()
        data:dict = fc.get_cargo() if which == 'Cargo' else fc.get_locker()

        output:str = ""
        if discord == True: output += "## "
        output += __("Carrier: {carrier_name} - {which}\n", lang=l).format(carrier_name=fc.overview['name'], which=which.title()) # LANG: fleet carrier materials header
        if fc.overview.get('currentStarSystem', "") != "":
            if discord == True: output += "### "
            output += __("Location: {system}\n", lang=l).format(system=fc.overview.get('currentStarSystem', 'Unknown')) # LANG: fleet carrier materials system line
        output += "\n"

        # Header row for table
        if discord == True: output += "```\n"
        header:list = []
        for col in tab['cols'].values():
            if col.get('discordWidth', None) == None: continue
            tmp:str = str_truncate(__(col['title'], lang=l), col['discordWidth'])
            fmt:str = "{val:"; fmt += "<" if col['align'] == tk.W else ">"; fmt += str(col['discordWidth']); fmt += "}"
            header.append(fmt.format(val=tmp))
        output += " | ".join(header) + "\n"
        w:int = sum([d.get('discordWidth', 0) for d in tab['cols'].values()])
        output += "-" * (w + (3 * (len(header) -1))) + "\n"
        #output += "-" * (sum(col['discordWidth']) + (3 * (len(col['discordWidth']) -1))) + "\n"

        # Table rows
        for item in data.get('inventory', {}).values():
            if type == 'Selling' and (item.get('price', 0) == 0 or item.get('stock', 0) == 0 or item.get('buyTotal', 0) > 0): continue
            if type == 'Buying' and item.get('outstanding', 0) == 0: continue
            if type == 'Both' and item.get('price', 0) == 0: continue

            line:list = []
            for f, col in tab['cols'].items():
                if col.get('discordWidth', None) == None: continue
                val:str = ""
                match f:
                    case "buy" if item.get("price", 0) > 0 and item.get("outstanding", 0) > 0: val = item.get("outstanding")
                    case "sell" if item.get("price", 0) > 0 and item.get("stock", 0) > 0: val = item.get("stock")
                    case _: val = item.get(f, " ")
                tmp:str = str_truncate(__(hfplus(val), lang=l), col['discordWidth'])
                fmt:str = "{val:"; fmt += "<" if col['align'] == tk.W else ">"; fmt += str(col['discordWidth']); fmt += "}"
                line.append(fmt.format(val=tmp))
            if line != []:
                output += " | ".join(line) + "\n"

        if discord == True: output += "```"
        return output
