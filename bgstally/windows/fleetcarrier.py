import tkinter as tk
from functools import partial
from tkinter import ttk
from datetime import datetime
from math import floor

from bgstally.constants import DATETIME_FORMAT_JSON, DATETIME_FORMAT_CARRIER, FONT_SMALL, COLOUR_WARNING, DiscordChannel, DiscordFleetCarrier
from bgstally.debug import Debug
from bgstally.fleetcarrier import FleetCarrier
from bgstally.utils import _, __, human_format, str_truncate, catch_exceptions
from bgstally.widgets import TextPlus, TreeviewPlus
from config import config # type: ignore

from thirdparty.colors import *
from thirdparty.Tooltip import ToolTip
from thirdparty.ScrollableNotebook import ScrollableNotebook
from thirdparty.tksheet import Sheet, num2alpha, natural_sort_key, ICON_DEL, ICON_ADD, ICON_SORT_DESC, ICON_SORT_ASC, ICON_REDO


class WindowFleetCarrier:
    """
    Handles the Fleet Carrier window.
    The window shows an overview of current carrier status and tabs for cargo, materials etc.
    Buttons are provided to copy information to the clipboard or post directly to discord.
    """

    def __init__(self, bgstally) -> None:
        self.bgstally:BGSTally = bgstally # type: ignore
        self.window:tk.Toplevel|None = None
        self.scale:float = 1.0

        self.tabs:dict = {
            'Summary': {
                'fields': ['service', 'enabled', 'status', 'name', 'taxation', 'salary', 'hiringPrice'],
                'cols': [
                    {'title': _('Service'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 225},
                    {'title': _('Enabled'), 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 85},
                    {'title': _('Status'), 'sort': 'name', 'align': tk.W, 'stretch': tk.NO, 'width': 100},
                    {'title': _('Crew Member'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 175},
                    {'title': _('Tax Rate'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 75},
                    {'title': _('Salary'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 85},
                    {'title': _('Hiring Cost'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 100},
                ],
                'names': {'vistagenomics': 'Vista Genomics', 'pioneersupplies': 'Pioneer Supplies',
                            'voucherredemption': 'Redemption', 'carriermanagement' : 'Carrier Management',
                            'stationmenu': 'Station Menu', 'Crew Lounge': 'Crew Lounge'},
                'ignore': ['stationmenu', 'carrierfuel', 'commodities', 'carriermanagement',
                           'dock', 'crewlounge', 'engineer', 'socialspace',
                            'contacts', 'registeringcolonisation', 'livery',
                            'lastEdit', 'faction', 'gender'],
                "func": self._summary
            },
            'Cargo': {
                'fields': ['locName', 'category', 'stock', 'buy', 'sell', 'price', 'stolen', 'mission'],
                'widths': [20, 14, 6, 6, 7, 7],
                'format': ["{val:<20}", "{val:<14}", "{val:>6}", "{val:>6}", "{val:>7}", "{val:>7}"],
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
                'widths': [20, 8, 5, 6, 7, 5],
                'format': ["{val:<20}", "{val:<8}", "{val:>5}", "{val:>6}", "{val:>7}", "{val:>5}"],
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
                'fields': ['starSystem', 'visitDurationSeconds', 'arrivalTime', 'departureTime', 'state'],
                'cols': [
                    {'title': _('System'), 'sort': 'name', 'align': tk.W, 'stretch': tk.YES, 'width': 250},
                    {'title': _('Duration'), 'sort': 'num', 'align': tk.E, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Arrived'), 'sort': 'datetime', 'align': tk.E, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Departed'), 'sort': 'datetime', 'align': tk.E, 'stretch': tk.NO, 'width': 150},
                    {'title': _('Status'), 'sort': 'name', 'align': tk.E, 'stretch': tk.NO, 'width': 100},
                ],
                'func': self._itinerary
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
        self.window.geometry(f"{int(850*self.scale)}x{int(600*self.scale)}")

        frame:ttk.Frame = ttk.Frame(self.window)
        if not config.get_bool('capi_fleetcarrier'):
            ttk.Label(frame, text=_("Some information cannot be updated. Enable Fleet Carrier CAPI Queries in File -> Settings -> Configuration"), foreground=COLOUR_WARNING).pack(anchor=tk.NW) # LANG: Label on carrier window

        self._show_overview(fc, frame)
        self._create_tabs(fc, frame)
        frame.pack(fill=tk.BOTH, expand=True)


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
            if v.get('buttons', False) == True:
                self._create_buttons(k, fr)
            v['func'](fc, v, fr)


    def _summary(self, fc:FleetCarrier, which:dict, frame:ttk.Frame) -> None:
        summary:dict = fc.get_summary()

        sections:dict = {'finances': _('Finances'),
                         'costs': _('Running Costs'),
                         'capacity': _('Capacity')}
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
                self._create_columns(summary[k], 4, summ, bg='white')
                if k != 'capacity':
                    separator:ttk.Separator = ttk.Separator(fr, orient=tk.HORIZONTAL)
                    separator.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

        services:dict = fc.get_services()

        table:TreeviewPlus = self._create_table(which['cols'], fr)
        for s, v in sorted(services.get('crew', {}).items()):
            if s in which['ignore']: continue
            row:list = []
            for c in which['fields']:
                if c in which['ignore']: continue
                val:str = ''
                match c:
                    case 'service': val = s.title() if s not in which['names'].keys() else which['names'][s]
                    case _: val = self._format(v.get(c, ""))
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
            self._create_columns(cargo['overview'], 4, summ, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for name, i in cargo['inventory'].items():
            line:list = []
            for c in which['fields']:
                val:str = ""
                match c:
                    case "buy" if i.get("price", 0) > 0 and i.get("outstanding", 0) > 0: val = i.get("outstanding")
                    case "sell" if i.get("price", 0) > 0 and i.get("stock", 0) > 0 and i.get('buyTotal') == 0: val = i.get("stock")
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
            self._create_columns(locker['overview'], 4, summ, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for cat, i in locker.get('inventory', {}).items():
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
            self._create_columns(itinerary['overview'], 10, summ, bg='white')

        table:TreeviewPlus = self._create_table(which['cols'], frame)
        for jump in itinerary.get('completed', []):
            row:list = []
            for c in which['fields']:
                row.append(self._format(jump.get(c)))
            table.insert("", 'end', values=row)


    def _format(self, val, type:str|None = None) -> str:
        """ A general customized formatting function for fc display """
        units:str = ''
        default:str = ''

        if isinstance(val, tuple): # (value, type, default, units)
            if len(val) > 1: type = val[1]
            if len(val) > 2: default = val[2]
            if len(val) > 3: units = val[3]
            if len(val) > 0: value = val[0]
        else:
            value = val
            if (isinstance(value, str) and re.match(value, r"^\d+-\d+-\d+ \d+\:\d+")): type = 'datetime'
            if isinstance(value, bool): type = 'bool'
            if isinstance(value, int) or isinstance(value, float): type = 'num'

        # Empty, zero or false we return an empty string so the display isn't full of "No" and "0" etc.
        if value == None or value == 0 or value == '' or value == False: return default

        ret:str = ""
        match type:
            case 'bool': # We're going to display Yes (blanks ar handled above)
                ret = _("Yes") # LANG: Yes

            case 'datetime': # If it's a datetime convert it from the json date format to our date format
                ret = datetime.strptime(str(value), DATETIME_FORMAT_JSON).strftime(DATETIME_FORMAT_CARRIER)

            case 'interval': # Approximated interval (no seconds, only show minutes if it's less than a day)
                days , rem = divmod(int(value), 60*60*24)
                hours, rem = divmod(rem, 60*60)
                mins, rem = divmod(rem, 60)
                tmp:list = []
                if floor(days) > 1: tmp.append(f"{floor(days)} days")
                elif int(days) > 0: tmp.append(f"1 day")
                if floor(hours) > 1: tmp.append(f"{floor(hours)} hours")
                elif int(hours) > 0: tmp.append(f" 1 hour")
                if len(tmp) < 2:
                    if floor(mins) > 1: tmp.append(f" {int(mins)} minutes")
                    elif mins > 0: tmp.append(f" 1 minute")
                ret = ' '.join(tmp)

            case 'num': # We only shorten/simplify large numbers. Smaller ones we just display with commas at thousands
                ret = human_format(int(value)) if int(value) > 100000 else f"{value:,}"

            case _: # Title case two words, leave longer strings as is
                ret = str(value).title() if str(value).count(' ') <= 2 else str(value)

        return ret + units


    def _create_columns(self, data:dict, maxcols:int, frame:ttk.Frame, bg:str='None') -> None:
        ''' Create grid of title/value pairs in columns and rows '''
        row:int = 0; col = 0
        lbl:ttk.Label

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
            col += 2
            if col >= maxcols*2:
                col = 0
                row += 1


    def _create_buttons(self, which:str, frame:ttk.Frame) -> None:
        """ Create tab buttons """

        # Simple internal helper functions.
        @catch_exceptions
        def _ctc(which:str, type:str|tk.StringVar) -> None:
            frame.clipboard_clear()
            frame.clipboard_append(self._get_as_text(which, type, False))

        @catch_exceptions
        def _post(which:str, type:str|tk.StringVar, btn:ttk.Button) -> None:
            fc: FleetCarrier = self.bgstally.fleet_carrier
            l:str = self.bgstally.state.discord_lang
            btn.config(state=tk.DISABLED)
            output:str = self._get_as_text(which, type, True)

            if len(output) > 1990: # Split it across multiple posts if it's too large.
                while len(output) > 1900:
                    split_at:int = output.rfind('\n', 0, 1000)
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

        def _post_type_selected(which:str, value:tk.StringVar) -> None: # Cargo or Materials
            self.bgstally.state.FcCargo.set(value) if which == 'Cargo' else self.bgstally.state.FcLocker.set(value)

        bar:ttk.Frame = ttk.Frame(frame)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        post_types:dict = {_("Buying") : DiscordFleetCarrier.BUYING, # LANG: Dropdown menu on activity window
                            _("Selling") : DiscordFleetCarrier.SELLING, # LANG: Dropdown menu on activity window
                            _("Both") : DiscordFleetCarrier.BOTH, # LANG: Dropdown menu on activity window
                            _("All") : DiscordFleetCarrier.ALL} # LANG: Dropdown menu on activity window

        strv:tk.StringVar = tk.StringVar(value=self.bgstally.state.FcCargo.get() if which == 'Cargo' else self.bgstally.state.FcLocker.get())
        menuv:ttk.OptionMenu = ttk.OptionMenu(bar, strv, strv.get(), *post_types.keys(),
                                              command=lambda val: _post_type_selected(which, val),
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


    def _post_type_selected(self, post_types: dict, value: str) -> None:
        """ The user has changed the dropdown to choose the type of data to post """
        k: str = next(k for k, v in post_types.items() if v == value)
        self.bgstally.state.DiscordFleetCarrier.set(k)


    @catch_exceptions
    def _get_as_text(self, which:str, type:str|tk.StringVar, discord:bool = False) -> str:
        """ Get the cargo or locker as text for pasting or posting to Discord """
        fc: FleetCarrier = self.bgstally.fleet_carrier
        l:str = self.bgstally.state.discord_lang if discord else ""
        tab:dict = self.tabs[which]
        if isinstance(type, tk.StringVar): type = type.get()
        data:dict = fc.get_cargo() if which == 'Cargo' else self.bgstally.fleet_carrier.get_locker()

        output:str = ""
        if discord == True: output += "## "
        output += __("Carrier: {carrier_name} - {which}\n", lang=l).format(carrier_name=fc.overview['name'], which=which.title()) # LANG: fleet carrier materials header
        if fc.overview.get('currentStarSystem', "") != "":
            if discord == True: output += "### "
            output += __("System: {system}\n", lang=l).format(system=fc.overview.get('currentStarSystem', 'Unknown')) # LANG: fleet carrier materials system line
        output += "\n"

        # Header row for table
        if discord == True: output += "```\n"
        header:list = []
        for i, fmt in enumerate(tab['format']):
            tmp:str = __(str_truncate(tab['cols'][i]['title'], tab['widths'][i]), lang=l)
            header.append(fmt.format(val=tmp))
        output += " | ".join(header) + "\n"
        output += "-" * (sum(tab['widths']) + (3 * (len(tab['widths']) -1))) + "\n"

        # Table rows
        for item in data.get('inventory', {}).values():
            if type == 'Selling' and (item.get('price', 0) == 0 or item.get('stock', 0) == 0 or item.get('buyTotal', 0) > 0): continue
            if type == 'Buying' and item.get('outstanding', 0) == 0: continue
            if type == 'Both' and item.get('price', 0) == 0: continue

            line:list = []
            for i, fmt in enumerate(tab['format']):
                val:str = ""
                match tab['fields'][i]:
                    case "buy" if item.get("price", 0) > 0 and item.get("outstanding", 0) > 0: val = item.get("outstanding")
                    case "sell" if item.get("price", 0) > 0 and item.get("stock", 0) > 0: val = item.get("stock")
                    case _: val = item.get(tab['fields'][i], " ")
                tmp:str = str_truncate(__(self._format(val), lang=l), tab['widths'][i])
                line.append(fmt.format(val=tmp))
            if line != []:
                output += " | ".join(line) + "\n"

        if discord == True: output += "```"
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
