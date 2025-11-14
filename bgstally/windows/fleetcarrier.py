import tkinter as tk
from functools import partial
from tkinter import ttk
from datetime import datetime
from math import floor

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

    def __init__(self, bgstally) -> None:
        self.bgstally:BGSTally = bgstally # type: ignore
        self.window:tk.Toplevel|None = None
        self.scale:float = 1.0

        self.post_types:dict = {'Cargo': ['All', True], 'Locker':['All', True]}
        self.tabs:dict = {
            'Finances': {
                'fields': [],
                'cols': [],
                "func": self._finances
            },
            'Cargo': {
                'fields': ['locName', 'category', 'stock', 'buy', 'sell', 'price', 'stolen', 'mission'],
                'cols': [
                    {'title': _('Commodity'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250},
                    {'title': _('Category'), 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Stock'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Buying'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Selling'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Price'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Stolen'), 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Mission'), 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70}
                ],
                "func": self._cargo,
                'buttons': True
            },
            'Locker': {
                'fields': ['locName', 'category', 'stock', 'buy', 'sell', 'price', 'mission'],
                'cols': [
                    {'title': _('Material'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250},
                    {'title': _('Category'), 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Stock'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Buying'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Selling'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Price'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 70},
                    {'title': _('Mission'), 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 70}
                ],
                "func": self._locker,
                'buttons': True
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
                'fields': ['service', 'enabled', 'name', 'tax', 'salary', 'hiringPrice'],
                'cols': [
                    {'title': _('Service'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250},
                    {'title': _('Enabled'), 'sort': 'name', 'align': tk.CENTER, 'stretch': tk.NO, 'width': 75},
                    {'title': _('Crew Member'), 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 250},
                    {'title': _('Tax Rate'), 'sort': 'num', 'align': tk.CENTER, 'stretch': tk.NO, 'width': 75},
                    {'title': _('Salary'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 100},
                    {'title': _('Hiring Cost'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 100},
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
        self.window.title(_("{plugin_name} - Carrier {carrier_name}").format(plugin_name=self.bgstally.plugin_name, carrier_name=fc.overview.get('name'))) # LANG: Carrier window title
        self.window.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.window.geometry(f"{int(800*self.scale)}x{int(500*self.scale)}")

        frame:ttk.Frame = ttk.Frame(self.window)
        frame.pack(fill=tk.BOTH, expand=True)
        if not config.get_bool('capi_fleetcarrier'):
            ttk.Label(frame, text=_("Some information cannot be updated. Enable Fleet Carrier CAPI Queries in File -> Settings -> Configuration"), foreground=COLOUR_WARNING).pack(anchor=tk.NW) # LANG: Label on carrier window

        self._show_overview(fc, frame)
        self._create_tabs(fc, frame)


    def _show_overview(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        """ Show the Fleet Carrier overview tab """
        summ:ttk.Frame = ttk.Frame(frame)
        summ.pack(fill=tk.X)
        self._create_columns(fc.get_overview(), 5, summ)


    def _create_tabs(self, fc:FleetCarrier, frame:ttk.Frame) -> None:
        """ Create and populate the Fleet Carrier tabs """

        style:ttk.Style = ttk.Style()
        style.configure("White.TNotebook.Tab", font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), padding=[10, 5], background='white')
        tabbar:ScrollableNotebook = ScrollableNotebook(frame, wheelscroll=False, tabmenu=False, style='White.TNotebook')
        tabbar.pack(fill=tk.X, padx=5, pady=5)

        for k, v in self.tabs.items():
            fr:ttk.Frame = ttk.Frame(tabbar, relief=tk.FLAT)
            fr.pack(fill=tk.BOTH, expand=1)
            tabbar.add(fr, text=_(k))
            if v.get('buttons', False) == True:
                self._create_buttons(k, fr)
            v['func'](fc, v, fr)

    def _finances(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        finances:dict = fc.get_finances()

        if finances.get('overview', None) != None:
            style:ttk.Style = ttk.Style()
            style.configure("White.TFrame", background='white')
            summ:ttk.Frame = ttk.Frame(frame, style="White.TFrame")
            summ.configure(padding=10)
            summ.pack(fill=tk.X)
            self._create_columns(finances['overview'], 20, summ, bg='white')

    def _services(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Create and display the Services tab """
        services:dict = fc.get_services()

        if services.get('overview', None) != None:
            style:ttk.Style = ttk.Style()
            style.configure("White.TFrame", background='white')
            summ:ttk.Frame = ttk.Frame(frame, style="White.TFrame")
            summ.configure(padding=10)
            summ.pack(fill=tk.X)
            self._create_columns(services['overview'], 1, summ, bg='white')

        names:dict = {'vistagenomics': 'Vista Genomics', 'pioneersupplies': 'Pioneer Supplies'}
        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for s, v in services['crew'].items():
            row:list = []
            for c in which['fields']:
                val:str = ''
                match c:
                    case 'service': val = s.title() if s not in names.keys() else names[s]
                    case 'tax': val = f"{v.get('taxation', 0)}%"
                    case 'enabled': val = v['crewMember'].get(c, '').title()
                    case _: val = self._format(v['crewMember'].get(c, ''))
                row.append(val)
            table.insert("", 'end', values=row)


    def _cargo(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Create and display the Cargo tab """
        cargo:dict = fc.get_cargo()

        if cargo.get('overview', None) != None:
            style:ttk.Style = ttk.Style()
            style.configure("White.TFrame", background='white')
            summ:ttk.Frame = ttk.Frame(frame, style="White.TFrame")
            summ.configure(padding=10)
            summ.pack(fill=tk.X)
            self._create_columns(cargo['overview'], 1, summ, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for name, i in cargo['inventory'].items():
            line:list = []
            for c in which['fields']:
                val:str = ""
                match c:
                    case "buy" if i.get("price", 0) > 0 and i.get("outstanding", 0) > 0: val = i.get("outstanding")
                    case "sell" if i.get("price", 0) > 0 and i.get("stock", 0) > 0: val = i.get("stock")
                    case _: val = i.get(c, " ")
                if i.get('stock', 0) > 0 or i.get('outstanding', 0) > 0:
                    line.append(self._format(val))
            if line != []:
                table.insert("", 'end', values=line, iid=i.get('locName'))


    def _locker(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Create and display the Locker tab """
        locker:dict = fc.get_locker()

        if locker.get('overview', None) != None:
            style:ttk.Style = ttk.Style()
            style.configure("White.TFrame", background='white')
            summ:ttk.Frame = ttk.Frame(frame, style="White.TFrame")
            summ.configure(padding=10)
            summ.pack(fill=tk.X)
            self._create_columns(locker['overview'], 2, summ, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for cat, i in locker.get('inventory').items():
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


    def _itinerary(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        """ Create and display the Itinerary tab """
        itinerary:dict = fc.get_itinerary()

        if itinerary.get('overview', None) != None:
            style:ttk.Style = ttk.Style()
            style.configure("White.TFrame", background='white')
            summ:ttk.Frame = ttk.Frame(frame, style="White.TFrame")
            summ.configure(padding=10)
            summ.pack(fill=tk.X)
            self._create_columns(itinerary['overview'], 1, summ, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for jump in itinerary.get('completed', []):
            row:list = []
            for c in which['fields']:
                val:str = ''
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
        """ A general customized formatting function for fc display """

        # Empty, zero or false we return an empty string so the display isn't full of "No" and "0" etc.
        if val == None or val == 0 or val == '' or val == False: return ''

        # If it's a datetime convert it from the json date format to our date format.
        if type == 'datetime' or (isinstance(type, str) and re.match(type, r"^\d+-\d+-\d+ \d+:=d+")):
            return datetime.strptime(val, DATETIME_FORMAT_JSON).strftime(DATETIME_FORMAT_CARRIER)

        # Approximated interval (no seconds, only show minutes if it's less than a day)
        if type == 'interval':
            days, rem = divmod(val, 60*60*24)
            hours, rem = divmod(rem, 60*60)
            mins, rem = divmod(rem, 60)

            ret = []
            if floor(days) > 1: ret.append(f"{floor(days)} days")
            elif int(days) > 0: ret.append(f"1 day")
            if floor(hours) > 1: ret.append(f"{floor(hours)} hours")
            elif int(hours) > 0: ret.append(f" 1 hour")
            if len(ret) < 2:
                if floor(mins) > 1: ret.append(f" {int(mins)} minutes")
                elif mins > 0: ret.append(f" 1 minute")
            return ' '.join(ret)

        # We're going to display Yes or leave it blank
        if isinstance(val, bool) or type == 'bool':
            return _("Yes") # LANG: Yes

        # We only shorten/simplify large numbers. Smaller ones we just display with commas at thousands
        if isinstance(val, int) or type == 'num':
            if val > 100000: return human_format(val)
            return f"{val:,}"

        # Title case two words, leave longer strings as is
        return val.title() if val.count(' ') <= 2 else val


    def _create_columns(self, data:dict, maxrows:int, frame:ttk.Frame, bg:str='None') -> None:
        ''' Create grid of title/value pairs in columns and rows '''
        row:int = 0; col = 0
        lbl:ttk.Label
        Debug.logger.debug(f"Creating columns for data: {data}")
        for k, v in data.items():
            if bg != 'None':
                lbl = ttk.Label(frame, text=_(k), font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), background=bg)
            else:
                lbl = ttk.Label(frame, text=_(k), font=(FONT_SMALL[0], FONT_SMALL[1], "bold"))
            lbl.grid(row=row, column=col, padx=20, pady=5, sticky=tk.W)
            txt:str = self._format(v)
            if bg != 'None':
                lbl = ttk.Label(frame, text=txt, font=FONT_SMALL, background=bg)
            else:
                lbl = ttk.Label(frame, text=txt, font=FONT_SMALL)
            lbl.grid(row=row, column=col+1, padx=10, pady=5, sticky=tk.W)
            row += 1
            if row >= maxrows:
                row = 0
                col += 2


    def _create_buttons(self, which:str, frame:ttk.Frame) -> None:
        """ Create tab buttons """

        # Simple internal helper functions.
        def _ctc(which:str, type:str) -> None:
            frame.clipboard_clear()
            frame.clipboard_append(self._get_as_text(which, type))

        def _post_type(which:str, value:str) -> None:
            self.post_types[which]['Post'][0] = value

        def _post(which, fc, lang) -> None:
            self.post_types[which][1].config(state=tk.DISABLED)
            title: str = __("Carrier {carrier_name}", lang=lang).format(carrier_name=fc.overview['name']) # LANG: Discord fleet carrier title
            description: str = ""

            fields: list = []
            fields.append({'name': __("System", lang=lang), 'value': fc.overview.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord fleet carrier field heading
            fields.append({'name': __("Docking", lang=lang), 'value': fc._readable(fc.overview.get('dockingAccess', ''), True), 'inline': True}) # LANG: Discord fleet carrier field heading
            fields.append({'name': __("Notorious Access", lang=lang), 'value': bool(fc.overview.get('notoriousAccess', True)), 'inline': True}) # LANG: Discord fleet carrier field heading
            self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)
            self.post_types[which][1].after(5000, _enable_post(which))

        def _discord_available() -> bool:
            return (self.bgstally.discord.valid_webhook_available(DiscordChannel.FLEETCARRIER_MATERIALS)
                    and self.bgstally.state.DiscordUsername.get() != "")

        def _enable_post(which:str) -> None:
            self.post_types[which][1].config(state=(tk.NORMAL if _discord_available() else tk.DISABLED))

        bar:ttk.Frame = ttk.Frame(frame)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        menu:dict = {_("Selling"): 'Selling', # LANG: Dropdown menu on cargo/materials window
                    _("Buying") : 'Buying', # LANG: Dropdown menu on cargo/materials window
                    _("Both"): 'Both', # LANG: Dropdown menu on cargo/materials windows
                    _("All") : 'All'} # LANG: Dropdown menu on cargo/materials windows
        strv:tk.StringVar = tk.StringVar(value=menu.get(self.post_types[which][0]))
        menuv:ttk.OptionMenu = ttk.OptionMenu(bar, strv, strv.get(), *menu.keys(), command=partial(_post_type, which), direction='above')

        tkb:ttk.Button = ttk.Button(bar, text=_("Copy to Clipboard"), command=partial(_ctc, which, strv)) # LANG: Button label
        tkb.pack(side=tk.LEFT, padx=5, pady=5)
        tkb:ttk.Button = ttk.Button(bar, text=_("Post to Discord"),
                                    command=partial(_post, which, self.bgstally.fleet_carrier, self.bgstally.state.discord_lang), # LANG: Button label
                                    state=(tk.NORMAL if _discord_available() else tk.DISABLED))
        self.post_types[which][1] = tkb
        tkb.pack(side=tk.RIGHT, padx=5, pady=5)
        if not _discord_available():
            ToolTip(tkb, text=_("Both the 'Post to Discord as' field and a Discord webhook{CR}must be configured in the settings to allow posting to Discord").format(CR="\n")) # LANG: Post to Discord button tooltip

        menuv.pack(side=tk.RIGHT, pady=5)


    def _create_table(self, cols:list, frame:ttk.Frame) -> TreeviewPlus:
        """ Create a treeview table with headings and columns """
        style = ttk.Style()
        style.configure("My.Treeview.Heading", font=(FONT_SMALL[0], FONT_SMALL[1], "bold"), background='lightgrey')

        # Dummy since callback is mandatory
        def _selected(self) -> None: return None

        table:TreeviewPlus = TreeviewPlus(frame, columns=[d['title'] for d in cols], show="headings", height=100, callback=_selected, datetime_format=DATETIME_FORMAT_CARRIER, style="My.Treeview")
        sb:ttk.Scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=table.yview)
        sb.pack(fill=tk.Y, side=tk.RIGHT)
        table.configure(yscrollcommand=sb.set)
        table.pack(fill=tk.X, expand=1)
        for column in cols:
            table.heading(column['title'], text=column['title'].title(), anchor=column['align'], sort_by=column['sort'])
            table.column(column['title'], anchor=column['align'], stretch=column['stretch'], width=column['width'])

        return table


    def _post_type_selected(self, post_types: dict, value: str):
        """ The user has changed the dropdown to choose the type of data to post """
        k: str = next(k for k, v in post_types.items() if v == value)
        self.bgstally.state.DiscordFleetCarrier.set(k)


    def _post_to_discord(self):
        """ Post Fleet Carrier materials list to Discord """
        fc: FleetCarrier = self.bgstally.fleet_carrier

        #title: str = __("Carrier {carrier_name}", lang=self.bgstally.state.discord_lang).format(carrier_name=fc.name) # LANG: Discord fleet carrier title
        #description: str = self._get_as_text(fc, True)

        #fields: list = []
        #fields.append({'name': __("System", lang=self.bgstally.state.discord_lang), 'value': fc.data.get('currentStarSystem', "Unknown"), 'inline': True}) # LANG: Discord fleet carrier field heading
        #fields.append({'name': __("Docking", lang=self.bgstally.state.discord_lang), 'value': fc.human_format_dockingaccess(True), 'inline': True}) # LANG: Discord fleet carrier field heading
        #fields.append({'name': __("Notorious Access", lang=self.bgstally.state.discord_lang), 'value': fc.human_format_notorious(True), 'inline': True}) # LANG: Discord fleet carrier field heading

        #self.bgstally.discord.post_embed(title, description, fields, None, DiscordChannel.FLEETCARRIER_MATERIALS, None)

        #self.btn_post_to_discord.after(5000, self._enable_post_button)


    @catch_exceptions
    def _get_as_text(self, which:str, type:str|tk.StringVar, discord:bool = False) -> str:
        """ Get the cargo or locker as text for pasting or posting to Discord """
        l:str = self.bgstally.state.discord_lang if discord else ""

        if isinstance(type, tk.StringVar):
            type = type.get()

        data:dict = self.bgstally.fleet_carrier.get_cargo() if which == 'Cargo' else self.bgstally.fleet_carrier.get_locker()

        output:str = ""
        output += __("Carrier {carrier_name} - {which}\n", lang=l).format(carrier_name=self.bgstally.fleet_carrier.overview['name'], which=which.title()) # LANG: Discord fleet carrier materials header
        output += __("System: {system}\n", lang=l).format(system=self.bgstally.fleet_carrier.overview.get('currentStarSystem', 'Unknown')) # LANG: Discord fleet carrier materials system line
        output += "\n"

        output += f"{__('Item', lang=l):<30} | {__('Category', lang=l):<20} | {__('Stock', lang=l):>7} | {__('Buying', lang=l):>7} | {__('Selling', lang=l):>7} | {__('Price', lang=l):>7}\n"
        for name, item in data.get('inventory', {}).items():
            if type == 'Selling' and (item.get('stock', 0) == 0 or item.get('price', 0) == 0): continue
            if type == 'Buying' and item.get('outstanding', 0) == 0: continue
            if type == 'Both' and item.get('stock', 0) == 0 and item.get('outstanding', 0) == 0: continue

            line:list = []
            for c in self.tabs[which]['fields']:
                val:str = ""
                match c:
                    case "buy" if item.get("price", 0) > 0 and item.get("outstanding", 0) > 0: val = item.get("outstanding")
                    case "sell" if item.get("price", 0) > 0 and item.get("stock", 0) > 0: val = item.get("stock")
                    case _: val = item.get(c, " ")
                line.append(self._format(val))
            if line != []:
                output += f"{__(line[0], lang=l):<30} | {__(line[1], lang=l):<20} | {line[2]:>7} | {line[3]:>7} | {line[4]:>7} | {line[5]:>7}\n"

        return output


    def _(self, text: str, discord:bool = False) -> str:
        """ Shortcut for translation """
        if discord:
            return __(text, lang=self.bgstally.state.discord_lang)
        return _(text)


# Just for translation
labels:dict = {"Finances": _("Finances"), # LANG: Tab label
                "Cargo": _("Cargo"), # LANG: Tab label
                'Locker': _('Locker'), # LANG: Tab label
                'Itinerary': _("Itinerary"), # LANG: Tab label
                "Services": _("Services"), # LANG: Commodity name header
            }
