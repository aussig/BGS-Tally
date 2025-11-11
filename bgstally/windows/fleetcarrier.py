import tkinter as tk
from functools import partial
from tkinter import ttk
from datetime import datetime

from bgstally.constants import FONT_TEXT, FONT_SMALL, COLOUR_WARNING, DiscordChannel
from bgstally.debug import Debug
from bgstally.fleetcarrier import FleetCarrier
from bgstally.utils import _, __, human_format, str_truncate, catch_exceptions
from bgstally.widgets import TextPlus, TreeviewPlus
from config import config # type: ignore

from thirdparty.colors import *
from thirdparty.Tooltip import ToolTip
from thirdparty.ScrollableNotebook import ScrollableNotebook
from thirdparty.tksheet import Sheet, num2alpha, natural_sort_key, ICON_DEL, ICON_ADD, ICON_SORT_DESC, ICON_SORT_ASC, ICON_REDO

DATETIME_FORMAT_CARRIER = "%Y-%m-%d %H:%M"
DATETIME_FORMAT_JSON = "%Y-%m-%d %H:%M:%S"
class WindowFleetCarrier:
    """
    Handles the Fleet Carrier window
    """

    def __init__(self, bgstally):
        self.bgstally:BGSTally = bgstally # type: ignore
        self.window:tk.Toplevel|None = None
        self.scale:float = 1.0
        
        self.post_types:dict = {'Cargo': ['All', True], 'Locker':['All', True]}
        self.tabs:dict = {
            'Cargo': {
                'fields': ['locName', 'category', 'stock', 'buy', 'sell', 'price', 'stolen', 'mission'],
                'cols': [
                    {'title': _('Commodity'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250},
                    {'title': _('Category'), 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Stock'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Buy'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Sell'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Price'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Stolen'), 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Mission'), 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70}                            
                ],
                "func": self._cargo,
                'butons': True
            },
            'Locker': {
                'fields': ['locName', 'category', 'quantity', 'buy', 'sell', 'price', 'mission'],
                'cols': [
                    {'title': _('Material'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250},
                    {'title': _('Category'), 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Quantity'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Buy'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Sell'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Price'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Mission'), 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70}                            
                ],
                "func": self._locker,
                'button': True
            },
            'Itinerary': {
                'fields': ['starsystem', 'visitDurationSeconds', 'arrivalTime', 'departureTime', 'state'],
                'cols': [
                    {'title': _('System'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250},
                    {'title': _('Duration'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Arrived'), 'sort': 'datetime', 'align': tk.E, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Departed'), 'sort': 'datetime', 'align': tk.E, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Status'), 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 100},
                ],
                'func': self._itinerary
            },
            'Services': {
                'fields': ['service', 'enabled', 'name', 'tax', 'salary'],
                'cols': [
                    {'title': _('Service'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250},
                    {'title': _('Enabled'), 'sort': 'name', 'align': tk.CENTER, 'stretch': tk.NO, 'width': 75},
                    {'title': _('Crew Member'), 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 250},
                    {'title': _('Tax Rate'), 'sort': 'num', 'align': tk.CENTER, 'stretch': tk.NO, 'width': 75},
                    {'title': _('Salary'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 100},
                ],
                "func": self._services
            },
        }

    @catch_exceptions
    def show(self) -> None:
        """ Show our window """
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            return

        fc:FleetCarrier = self.bgstally.fleet_carrier
        self.scale = config.get_int('ui_scale') / 100.00
        self.window = tk.Toplevel(self.bgstally.ui.frame)
        self.window.title(_("{plugin_name} - Carrier {carrier_name}").format(plugin_name=self.bgstally.plugin_name, carrier_name=fc.name)) # LANG: Carrier window title
        self.window.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.window.geometry(f"{int(800*self.scale)}x{int(500*self.scale)}")

        frame:ttk.Frame = ttk.Frame(self.window)
        frame.pack(fill=tk.BOTH, expand=True)
        if not config.get_bool('capi_fleetcarrier'):
            ttk.Label(frame, text=_("Some information cannot be updated. Enable Fleet Carrier CAPI Queries in File -> Settings -> Configuration"), foreground=COLOUR_WARNING).pack(anchor=tk.NW) # LANG: Label on carrier window

        self._show_summary(fc, frame)
        self._create_tabs(fc, frame)


    def _show_summary(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        """ Show the Fleet Carrier overview tab """
        row:int = 0; col = 0
        summ:ttk.Frame = ttk.Frame(frame)
        summ.pack(fill=tk.X)

        sum:dict = fc.get_summary()
        for k, v in sum.items():                       
            lbl = ttk.Label(summ, text=_(k), font=(FONT_SMALL[0], FONT_SMALL[1], "bold"))
            lbl.grid(row=row, column=col, padx=10, pady=5, sticky=tk.W)
            col += 1
            txt:str = self._format(v) if k != 'Arrival' else self._format(v, 'datetime')
            lbl = ttk.Label(summ, text=txt, font=FONT_SMALL)
            lbl.grid(row=row, column=col, padx=10, pady=5, sticky=tk.W)
            col += 1
            if col >= 6:
                col = 0
                row += 1

    def _create_buttons(self, which:str, frame:ttk.Frame) -> None:
        """ Create tab buttons """

        # Simple internal helper functions.
        def _ctc(what:str, frame:ttk.Frame) -> None:
            frame.clipboard_clear()
            frame.clipboard_append(what)

        def _post_type(which:str, value:str) -> None:
            self.post_types[which]['Post'][0] = value

        def _post(which, fc, lang) -> None:
            self.post_types[which][1].config(state=tk.DISABLED)
            title: str = __("Carrier {carrier_name}", lang=lang).format(carrier_name=fc.name) # LANG: Discord fleet carrier title
            description: str = ""

            fields: list = []
            fields.append({'name': __("System", lang=lang), 'value': fc.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord fleet carrier field heading
            fields.append({'name': __("Docking", lang=lang), 'value': fc._readable(fc.data.get('dockingAccess', ''), True), 'inline': True}) # LANG: Discord fleet carrier field heading
            fields.append({'name': __("Notorious Access", lang=lang), 'value': bool(fc.data.get('notoriousAccess', True)), 'inline': True}) # LANG: Discord fleet carrier field heading
            self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)
            self.post_types[which][1].after(5000, _enable_post(which))

        def _discord_available() -> bool:
            return (self.bgstally.discord.valid_webhook_available(DiscordChannel.FLEETCARRIER_MATERIALS)
                    and self.bgstally.state.DiscordUsername.get() != "")

        def _enable_post(which:str) -> None:
            self.post_types[which][1].config(state=(tk.NORMAL if _discord_available() else tk.DISABLED))


        fr:ttk.Frame = ttk.Frame(frame)
        fr.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        tkb:ttk.Button = ttk.Button(fr, text=_("Copy to Clipboard"), command=partial(_ctc, 'test', fr)) # LANG: Button label
        tkb.pack(side=tk.LEFT, padx=5, pady=5) 
        tkb:ttk.Button = ttk.Button(fr, text=_("Post to Discord"), 
                                    command=partial(_post, which, self.bgstally.fleet_carrier, self.bgstally.state.discord_lang), # LANG: Button label
                                    state=(tk.NORMAL if _discord_available() else tk.DISABLED))
        self.post_types[which][1] = tkb
        tkb.pack(side=tk.RIGHT, padx=5, pady=5)
        if not _discord_available():
            ToolTip(tkb, text=_("Both the 'Post to Discord as' field and a Discord webhook{CR}must be configured in the settings to allow posting to Discord").format(CR="\n")) # LANG: Post to Discord button tooltip
        menu:dict = {_("All") : 'All', # LANG: Dropdown menu on cargo/materials windows
                    _("Selling"): 'Selling', # LANG: Dropdown menu on cargo/materials window
                    _("Buying") : 'Buying'} # LANG: Dropdown menu on cargo/materials window

        strv:tk.StringVar = tk.StringVar(value=menu.get(self.post_types[which][0]))
        menuv:ttk.OptionMenu = ttk.OptionMenu(fr, strv, strv.get(), *menu.keys(), command=partial(_post_type, which), direction='above')
        menuv.pack(side=tk.RIGHT, pady=5)
        
    
    def _create_tabs(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        """ Create and populate the Fleet Carrier tabs """
        style:ttk.Style = ttk.Style()
        style.configure("My.TNotebook.Tab", font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), padding=[10, 5])
        tabbar:ScrollableNotebook = ScrollableNotebook(frame, wheelscroll=False, tabmenu=False, style='My.TNotebook')
        tabbar.pack(fill=tk.X, padx=5, pady=5)

        for k, v in self.tabs.items():
            fr:ttk.Frame = ttk.Frame(tabbar)
            fr.pack(fill=tk.BOTH, expand=1)
            tabbar.add(fr, text=_(k))
            v['func'](fc, v, fr)

            if v.get('buttons', False):
                self._create_buttons(k, frame)


    def _create_table(self, cols:list, frame:ttk.Frame) -> TreeviewPlus:
        """ Create a table with headings and columns """
        style = ttk.Style()
        style.configure("My.Treeview.Heading", font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), background='lightgrey')

        # Dummy since callback is mandatory
        def _selected(self) -> None: return None
    
        table:TreeviewPlus = TreeviewPlus(frame, columns=[d['title'] for d in cols], show="headings", height=100, callback=_selected, datetime_format=DATETIME_FORMAT_CARRIER, style="My.Treeview")
        #treeview.bind('<<TreeviewSelect>>', partial(self._selected, treeview))
        sb:tk.Scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=table.yview)
        sb.pack(fill=tk.Y, side=tk.RIGHT)
        table.configure(yscrollcommand=sb.set)
        table.pack(fill=tk.BOTH, expand=1)
        for column in cols:
            table.heading(column['title'], text=column['title'].title(), anchor=column['align'], sort_by=column['sort'])
            table.column(column['title'], anchor=column['align'], stretch=column['stretch'], width=column['width'])
        return table
    

    def _services(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Services tab """
        names:dict = {'vistagenomics': 'Vista Genomics', 'pioneersupplies': 'Pioneer Supplies'}
        table:TreeviewPlus = self._create_table(which['cols'], frame)        
        services:dict = fc.get_services()
        for s, v in services.items():
            row:list = []
            for c in which['fields']:
                val = ''
                match c:
                    case 'service': val = s.title() if s not in names.keys() else names[s]
                    case 'tax': val = f"{v.get('taxation', 0)}%"
                    case 'enabled': val = v['crewMember'].get(c, '').title()
                    case _: val = self._format(v['crewMember'].get(c, ''))
                row.append(val)
            table.insert("", 'end', values=row)


    def _cargo(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Cargo tab """        
        table:TreeviewPlus = self._create_table(which['cols'], frame)
        cargo:dict = fc.get_cargo()
        for comm, i in cargo.items():
            row:list = []
            for c in which['fields']:
                val:str = ""
                match c:
                    case "buy" if i.get("price", 0) > 0 and i.get("outstanding", 0) > 0: val = i.get("outstanding")
                    case "sell" if i.get("price", 0) > 0 and i.get("stock", 0) > 0: val = i.get("stock")
                    case _: val = i.get(c, " ")
                if i.get('stock', 0) > 0 or i.get('outstanding', 0) > 0:
                    row.append(self._format(val))
            if row != []:
                table.insert("", 'end', values=row, iid=i.get('locName'))


    def _locker(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Locker tab """
        table:TreeviewPlus = self._create_table(which['cols'], frame)
        locker:dict = fc.get_locker()
        
        for cat, i in locker.items():
            row:list = []
            for c in which['fields']:
                val:str = ""
                match c:
                    case "buy" if i.get("price", 0) > 0 and i.get("outstanding", 0) > 0: val = i.get("outstanding")
                    case "sell" if i.get("price", 0) > 0 and i.get("quantity", 0) > 0: val = i.get("quantity")
                    case _: val = i.get(c, " ")
                if i.get('quantity', 0) > 0 or i.get('outstanding', 0) > 0:
                    row.append(self._format(val))
            if row != []:
                table.insert("", 'end', values=row, iid=i.get('locName'))
                
    
    def _itinerary(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Itinerary tab """
        table:TreeviewPlus = self._create_table(which['cols'], frame)
        itinerary:dict = fc.get_itinerary()
        for jump in itinerary.get('completed', []):
            row:list = []
            for c in which['fields']:
                val = ''
                match c:
                    case 'visitDurationSeconds':
                        val = self._format(jump.get(c), 'interval')
                    case 'arrivalTime' | 'departureTime':
                        val = self._format(jump.get(c), 'datetime')
                    case _:
                        val = self._format(jump.get(c))
                row.append(val)
            table.insert("", 'end', values=row)


    def _format(self, val, type:str|None = None) -> str:
        """ General formatting function """        
        if val == None or val == 0 or val == False: return ''
        
        if type == 'datetime':
            return datetime.strptime(val, DATETIME_FORMAT_JSON).strftime(DATETIME_FORMAT_CARRIER)
        if type == 'interval':
            days, rem = divmod(val, 60*60*24)
            hours, rem = divmod(rem, 60*60)
            mins, rem = divmod(rem, 60)
            ret = ''
            if int(days) > 0: ret += f" {int(days)} days"
            if int(hours) > 0: ret += f" {int(hours)} hours"
            if ret == '': ret += f" {int(mins)} minutes"
            return ret
        if isinstance(val, bool) or type == 'bool':
            return _("Yes") # LANG: Yes
        if isinstance(val, int) or type == 'num':
            if val > 100000: return human_format(val)
            return f"{val:,}"
        if val.count(' ') > 2:
            return val
        return val.title()


    def _post_type_selected(self, post_types: dict, value: str):
        """ The user has changed the dropdown to choose the type of data to post """
        k: str = next(k for k, v in post_types.items() if v == value)
        self.bgstally.state.DiscordFleetCarrier.set(k)


    def _post_to_discord(self):
        """
        Post Fleet Carrier materials list to Discord
        """
        fc: FleetCarrier = self.bgstally.fleet_carrier

        #title: str = __("Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=fc.name) # LANG: Discord fleet carrier title
        #description: str = self._get_as_text(fc, True)

        #fields: list = []
        #fields.append({'name': __("System", lang=self.bgstally.state.discord_lang), 'value': fc.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord fleet carrier field heading
        #fields.append({'name': __("Docking", lang=self.bgstally.state.discord_lang), 'value': fc.human_format_dockingaccess(True), 'inline': True}) # LANG: Discord fleet carrier field heading
        #fields.append({'name': __("Notorious Access", lang=self.bgstally.state.discord_lang), 'value': fc.human_format_notorious(True), 'inline': True}) # LANG: Discord fleet carrier field heading

        #self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)

        #self.btn_post_to_discord.after(5000, self._enable_post_button)


# Just for translation
labels:dict = {"Finances": _("Finances"), # LANG: Tab label
                "Cargo": _("Cargo"), # LANG: Tab label
                'Locker': _('Locker'), # LANG: Tab label
                'Itinerary': _("Itinerary"), # LANG: Tab label
                "Services": _("Services"), # LANG: Commodity name header 
            }
