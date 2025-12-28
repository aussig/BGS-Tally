import tkinter as tk
import tkinter.font as tkFont
import webbrowser
import re
import sys
from requests import Response
from functools import partial
from math import ceil
from tkinter import ttk
from urllib.parse import quote

from bgstally.constants import TAG_OVERLAY_HIGHLIGHT, FONT_SMALL, RequestMethod, CommodityOrder, ProgressUnits, ProgressView, CheckStates
from bgstally.debug import Debug
from bgstally.utils import _, str_truncate, catch_exceptions, human_format
from bgstally.ravencolonial import RavenColonial
from bgstally.requestmanager import BGSTallyRequest
from config import config # type: ignore
from thirdparty.Tooltip import ToolTip
from thirdparty.tksheet import Sheet, natural_sort_key

class ProgressWindow:
    '''
    Frame for displaying colonisation construction progress.

    This creates a frame within the ED:MC main window, as part of the BGS-Tally section,
    and displays the commodities required for a build (or all tracked builds),
    their amounts, and progress towards completion.

    It also provides a progress bar for the overall progress of the build (or builds).
    '''
    def __init__(self, bgstally) -> None:
        self.bgstally = bgstally
        self.colonisation = None

        # The headings for each column, with the meanings for each unit type.
        # These are saved in the colonisation json file.
        self.headings:list = [
            {
                'Column' : 'Commodity',
                'Label' : f"{_('Commodity'): <40}", # LANG: Commodity
                'Tooltip' : f"{_('Commodity')}"
            },
            {
                'Column' : 'Required',
                'Label': f"{_('Required'): >13}", # LANG: Required amount
                'Tooltip' : f"{_('Total quantity required')}" # LANG: required amount tooltip
            },
            {
                'Column' : 'Delivered',
                'Label': f"{_('Delivered'): >13}", # LANG: Delivered amount
                'Tooltip' : f"{_('Total quantity delivered')}" # LANG: delivered amount tooltip
            },
            {
                'Column' : 'Remaining',
                'Label': f"{_('Remaining'): >12}", # LANG: Amount remaining
                'Tooltip' : f"{_('Amount remaining to be delivered')}" # LANG: Amount remaining tooltip
            },
            {
                'Column' : 'Purchase',
                'Label': f"{_('Purchase'): >13}", # LANG: Amount to buy
                'Tooltip' : f"{_('Amount left to buy')}" # LANG: Amount left to buy
            },
            {
                'Column' : 'Cargo',
                'Label': f"{_('Cargo'): >13}", # LANG: Cargo amount
                'Tooltip' : f"{_('Amount in current cargo')}" # LANG: Cargo amount tooltip
            },
            {
                'Column' : 'Carrier',
                'Label': f"{_('Carrier'): >13}", # LANG: Carrier amount
                'Tooltip' : f"{_('Amount in linked fleet carrier(s)')}" # LANG: Carrier amount tooltip
            },
            {
                'Column' : 'BuyOrder',
                'Label': f"{_('Buy Orders'): >13}", # LANG: Carrier buy order amount
                'Tooltip' : f"{_('Amount outstanding in carrier buy orders')}" # LANG: Carrier buy order tooltip
            }
        ]
        self.ordertts:list = [_('Alphabetical order'), _('Category order'), _('Quantity order')]

        self.markets:dict = {
            'systemName' : {'header': _('System'), 'width': 175, 'align': "left"},      # LANG: System Name heading
            'stationName' : {'header': _('Station'), 'width': 175, 'align': "left"},    # LANG: Station name heading
            'distance': {'header': _('Dist (ly)'), 'width': 50, 'align': "center"},     # LANG: System distance heading
            'distanceToArrival': {'header': _('Arr (ls)'), 'width': 50, 'align': "center"}, # LANG: station distance from arrival heading
            'distance': {'header': _('Dist (ly)'), 'width': 50, 'align': "center"},     # LANG: System distance heading
            'distanceToArrival': {'header': _('Arr (ls)'), 'width': 50, 'align': "center"}, # LANG: station distance from arrival heading
            'type': {'header': _('Type'), 'width': 35, 'align': "center"},              # LANG: Station type (O=Orbital, S=Surface, C=Carrier)
            'padSize': {'header': _('Pad'), 'width': 35, 'align': "center"},            # LANG: Pad size (L, M, S)
            'count': {'header': _('Count'), 'width':45, 'align': "center"},             # LANG: Count of commodities available
            'quantity': {'header': _('Amt (t)'), 'width':55, 'align': "center"},        # LANG: Tonnes of needed commodities available
            'commodities': {'header': _('Commodities'), 'width': 565, 'align': "left"}  # LANG: List of commodities available
            }

        self.colors:dict = {'L' : '#d4edbc', 'M' : '#dbe5ff', 'O' : '#d5deeb', 'S' : '#ebe6db', 'C' : '#e6dbeb'}

        self.links:dict = {'Inara': 'https://inara.cz/elite/starsystem/search/?search={StarSystem}',
                           'Spansh': 'https://www.spansh.co.uk/station/{MarketID}'
        }

        # Initialise the default units & column types
        self.units:list = [CommodityOrder.ALPHA, ProgressUnits.QTY, ProgressUnits.QTY, ProgressUnits.QTY]
        self.columns:list = [0, 2, 3, 5]
        self.collbls:list = [None, None, None, None] # Column headings
        self.coltts: list = [None, None, None, None]

        # By removing the carrier from here we remove it everywhere
        if not self.bgstally.fleet_carrier.available():
            self.headings.pop() # Carrier
            self.headings.pop() # Buy Orders

        # UI components
        self.frame:tk.Frame
        self.mkts_fr:tk.Toplevel|None = None # Markets popup window
        self.frame_row:int = 0 # Row in the parent frame
        self.table_frame:tk.Frame # Table frame
        self.title:tk.Label # Title object
        self.titlett:ToolTip # Title tooltip
        self.rows:list = []
        self.progbar:ttk.Progressbar # Overall progress bar
        self.progvar:tk.IntVar = tk.IntVar(value=0)
        self.progress:int = 0 # Thread-safe version of progress percentage
        self.build_index:int = 0 # Which build we're showing
        self.view:ProgressView = ProgressView.REDUCED # Full, reduced, or no list of commodities
        self.viewtt:ToolTip # View tooltip
        self.comm_order:CommodityOrder = CommodityOrder.ALPHA # Commodity order


    @catch_exceptions
    def create_frame(self, parent_frame:tk.Frame, start_row:int, column_count:int) -> None:
        ''' Create the progress frame. This is called by ui.py on startup. '''
        def bind_mousewheel(event: tk.Event) -> None:
            """ Scroll pane mousewheel bind on mouseover """

            if sys.platform in ('linux', 'cygwin', 'msys'):
                scroll_canvas.bind_all('<Button-4>', on_mousewheel)
                scroll_canvas.bind_all('<Button-5>', on_mousewheel)
            else:
                scroll_canvas.bind_all('<MouseWheel>', on_mousewheel)

        def unbind_mousewheel(event: tk.Event) -> None:
            """ Scroll pane mousewheel unbind on mouseout """

            if sys.platform in ('linux', 'cygwin', 'msys'):
                scroll_canvas.unbind_all('<Button-4>')
                scroll_canvas.unbind_all('<Button-5>')
            else:
                scroll_canvas.unbind_all('<MouseWheel>')

        def on_mousewheel(event: tk.Event) -> None:
            """ Scroll pane mousewheel event handler """

            shift = (event.state & 0x1) != 0 #type: ignore
            scroll = 0
            if event.num == 4 or event.delta == 120:
                scroll = -1
            if event.num == 5 or event.delta == -120:
                scroll = 1
            if shift:
                scroll_canvas.xview_scroll(scroll, 'units')
            else:
                scroll_canvas.yview_scroll(scroll, 'units')

        bgs_cols:int = 6
        self.colonisation = self.bgstally.colonisation

        self.frame_row = start_row
        frame:tk.Frame = tk.Frame(parent_frame)
        frame.grid(row=start_row, column=0, columnspan=bgs_cols, sticky=tk.EW)
        self.frame = frame

        row:int = 0; col:int = 0

        # Overall progress bar chart
        scale:float = config.get_int('ui_scale') / 100.00
        y=tk.LabelFrame(frame, border=1, height=10, width=int(398*scale))
        y.grid(row=row, column=col, pady=0, sticky=tk.EW)
        y.grid_rowconfigure(0, weight=1)
        y.grid_propagate(False)

        self.progbar:ttk.Progressbar = ttk.Progressbar(y, orient=tk.HORIZONTAL, variable=self.progvar, maximum=100, length=int(398*scale), mode='determinate')
        self.progtt:ToolTip = ToolTip(self.progbar, text=_("Progress")) # LANG: progress tooltip
        self.progbar.grid(row=0, column=0, pady=0, ipady=0, sticky=tk.EW)
        self.progbar.rowconfigure(0, weight=1)
        row += 1; col = 0

        builds:tk.Frame = tk.Frame(frame)
        builds.grid(row=row, column=0, sticky=tk.EW)
        builds.grid_columnconfigure(0, weight=0)
        builds.grid_columnconfigure(1, weight=5)
        builds.grid_columnconfigure(2, weight=0)
        builds.grid_columnconfigure(3, weight=0)
        builds.grid_columnconfigure(4, weight=0)
        c:int = 0
        lbl:tk.Label = tk.Label(builds, text=_("Builds") + ":", anchor=tk.W) # LANG: Builds/bases
        lbl.grid(row=0, column=c, sticky=tk.W)
        self._set_weight(lbl)
        c += 1
        self.title = tk.Label(builds, text=_("None"), justify=tk.CENTER, anchor=tk.CENTER, cursor="hand2") # LANG: None
        #self.title.config(foreground=config.get_str('dark_text') if config.get_int('theme') > 0 else 'black')
        self.title.bind("<Button-1>", partial(self.event, "copy"))
        self.title.bind("<Button-3>", partial(self._context_menu))
        self.title.grid(row=0, column=c, sticky=tk.EW)
        self.titlett:ToolTip = ToolTip(self.title, text=f"{_('Current build')}, {_('left click to copy, right click menu')}") # LANG: tooltip for the build name
        c += 1

        prev_btn:tk.Label = tk.Label(builds, image=self.bgstally.ui.image_icon_left_arrow, cursor="hand2")
        prev_btn.bind("<Button-1>", partial(self.event, "prev"))
        prev_btn.grid(row=0, column=c, sticky=tk.W)
        ToolTip(prev_btn, text=_("Show previous build")) # LANG: tooltip for the previous build icon
        c += 1

        view_btn:tk.Label = tk.Label(builds, image=self.bgstally.ui.image_icon_change_view, cursor="hand2")
        view_btn.bind("<Button-1>", partial(self.event, "change"))
        view_btn.grid(row=0, column=c, sticky=tk.E)
        self.viewtt:ToolTip = ToolTip(view_btn, text=_("Cycle commodity list details") + " (" + self.view.name.title() +")") # LANG: tooltip for the commodity header
        c += 1

        next_btn:tk.Label = tk.Label(builds, image=self.bgstally.ui.image_icon_right_arrow, cursor="hand2")
        next_btn.bind("<Button-1>", partial(self.event, "next"))
        next_btn.grid(row=0, column=c, sticky=tk.E)
        ToolTip(next_btn, text=_("Show next build")) # LANG: tooltip for the next build icon

        row += 1; col = 0

        # Commodity table frame
        table_frame:tk.Frame = tk.Frame(frame)
        table_frame.grid(row=row, column=col, sticky=tk.NSEW)
        self.table_frame = table_frame

        if self.bgstally.state.EnableProgressScrollbar.get() == CheckStates.STATE_ON:
            Debug.logger.debug(f"Using scrollbar")
            height=int((int(self.bgstally.state.ColonisationMaxCommodities.get())+2)*21*scale)
            scroll_canvas = tk.Canvas(table_frame, height=height, highlightthickness=0)
            scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=scroll_canvas.yview)
            table_frame.update()
            scrollable_frame = tk.Frame(scroll_canvas, width=table_frame.winfo_width())

            scrollable_frame.bind(
                '<Configure>',
                lambda e: scroll_canvas.configure(
                    scrollregion=scroll_canvas.bbox('all')
                )
            )
            scroll_canvas.bind('<Enter>', bind_mousewheel)
            scroll_canvas.bind('<Leave>', unbind_mousewheel)

            scroll_canvas.update()
            scroll_canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW, width=table_frame.winfo_width())
            scroll_canvas.configure(yscrollcommand=scrollbar.set)
            scroll_canvas.grid(row=1, column=0, sticky=tk.E)
            #scroll_canvas.grid_rowconfigure(1, weight=1)
            scroll_canvas.columnconfigure(0, weight=3)
            scroll_canvas.columnconfigure(1, weight=1)
            scroll_canvas.columnconfigure(2, weight=1)
            scroll_canvas.columnconfigure(3, weight=1)
            scrollbar.grid(row=1, column=5, sticky=tk.NS, ipadx=0, padx=0)
            #if config.get_int('theme') == 1:
            #    scroll_canvas.configure(background='black')
            #    scrollable_frame.configure(background='black')
                #scrollbar.configure(background='black', activebackground='black', troughcolor='black', highlightbackground='black')
            table = scrollable_frame
            # We have to make the column less wide to fit the scrollbar in
            self.headings[0]['Label'] = f"{_('Commodity'): <32}"
            self.scroll_canvas = scroll_canvas
        else:
            Debug.logger.debug(f"Not using scrollbar")
            table = tk.Frame(table_frame)
            table.grid(row=1, column=0, sticky=tk.NSEW)

        row = 0
        # Column headings
        for col, v in enumerate(self.columns):
            if v >= len(self.headings): v = 0
            lbl = tk.Label(table, text=self.headings[v].get('Label'), cursor='hand2')
            lbl.bind("<Button-1>", partial(self.change_view, col, 'Column'))
            lbl.bind("<Button-3>", partial(self.change_view, col, 'Units'))

            #lbl.config(foreground=config.get_str('dark_text') if config.get_int('theme') > 0 else 'black')
            #if config.get_int('theme') == 1: lbl.config(background='black')
            self._set_weight(lbl)
            lbl.grid(row=row, column=col, sticky=tk.EW if col == 0 else tk.E, padx=(0,5))

            self.collbls[col] = lbl
            self.coltts[col] = ToolTip(lbl, text=self.headings[v].get('Tooltip'))
        row += 1

        # Go through the complete list of possible commodities and make a row for each and hide it.
        for c in self.colonisation.get_commodity_list():
            r:dict = {}

            for col, v in enumerate(self.columns):
                lbl:tk.Label = tk.Label(table, text='', cursor="hand2")
                #lbl.config(foreground=config.get_str('dark_text') if config.get_int('theme') > 0 else 'black')
                #if config.get_int('theme') == 1: lbl.config(background='black')
                lbl.grid(row=row, column=col, sticky=tk.W if col == 0 else tk.E, padx=(0,5))
                #if row == 0:
                #    lbl.bind("<Button-1>", partial(self.link, c, None))
                #    lbl.bind("<Button-3>", partial(self.event, self.colonisation.get_commodity(c)))
                #    ToolTip(lbl, text=_("Left click for Inara market, right click to copy")) # LANG: tooltip for the inara market commodity links and copy to clipboard
                #    lbl.config(cursor='hand2', foreground=config.get_str('dark_text') if config.get_int('theme') == 1 else 'black')

                r[col] = lbl
            self.rows.append(r)
            row += 1
        row += 1

        # Totals at the bottom
        r:dict = {}
        for col, v in enumerate(self.columns):
            r[col] = tk.Label(table, text=_("Total")) # LANG: Total amounts
            r[col].grid(row=row, column=col, sticky=tk.W if col == 0 else tk.E, padx=(0,5))
            #r[col].config(foreground=config.get_str('dark_text') if config.get_int('theme') > 0 else 'black')
            #if config.get_int('theme') == 1: r[col].config(background='black')
            self._set_weight(r[col])
        self.rows.append(r)

        # No builds or no commodities so hide the frame entirely
        tracked:list = self.colonisation.get_tracked_builds()
        if len(tracked) == 0 or len(self.colonisation.get_required(tracked)) == 0:
            Debug.logger.info("No builds or commodities, hiding progress frame")
            frame.grid_remove()
            return

        self.update_display()


    @catch_exceptions
    def _context_menu(self, event: tk.Event) -> None:
        """ Display the context menu when right-clicked."""

        menu = tk.Menu(tearoff=tk.FALSE)
        menu.add_command(label=_('Copy to Clipboard'), command=partial(self.event, "copy"))  # LANG: build popup menu
        #menu.add_command(label=_('Post to Discord'), command=partial(self.event, "post"))  # LANG: build popup menu

        tracked:list = self.colonisation.get_tracked_builds()
        if self.build_index < len(tracked):
            menu.add_separator()
            b:dict = tracked[self.build_index]
            if b.get('ProjectID', None) != None:
                menu.add_command(label=_('Open in RavenColonial'), command=partial(webbrowser.open, 'https://ravencolonial.com/#build='+b.get('ProjectID','')))  # LANG: build popup menu

            if b.get('MarketID', None) != None:
                params:dict = {k: quote(str(v)) if str(k) != 'Layout' else str(v).strip().lower().replace(" ","_") for k, v in b.items()}
                for k, v in self.links.items():
                    menu.add_command(label=_("Open in {k}").format(k=k), command=partial(webbrowser.open, v.format(**params)))  # LANG: build popup menu

        menu.post(event.x_root, event.y_root)


    @catch_exceptions
    def as_text(self, discord:bool = True) -> str:
        ''' Return a text representation of the progress window '''
        if not hasattr(self.bgstally, 'colonisation'):
            return _("No colonisation data available") # LANG: No colonisation data available
        self.colonisation = self.bgstally.colonisation

        tracked:list = self.colonisation.get_tracked_builds()
        required:dict = self.colonisation.get_required(tracked)
        delivered:dict = self.colonisation.get_delivered(tracked)
        if len(tracked) == 0 or self.colonisation.cargo_capacity < 8:
            return "" # LANG: No builds or commodities being tracked

        if self.build_index >= len(required): self.build_index = 0

        output:str = ""
        if discord:
            output = "```" + _("All builds") + "\n" # LANG: all tracked builds
        else:
            output = TAG_OVERLAY_HIGHLIGHT + _("All builds") + "\n" # LANG: all tracked builds

        if self.build_index < len(tracked):
            b:dict = tracked[self.build_index]
            sn:str = b.get('Plan', _('Unknown')) # Unknown system name
            bn:str = b.get('Name', '') if b.get('Name','') != '' else b.get('Base Type', '')
            if discord:
                output = f"```{sn}, {bn}\n"
            else:
                output = f"{TAG_OVERLAY_HIGHLIGHT}{sn}\n{TAG_OVERLAY_HIGHLIGHT}{str_truncate(bn, 30, loc='left')}\n"

        output += f"{_('Progress')}: {self.progress:.0f}%\n"
        output += "\n"
        if discord:
            output += f"{_('Commodity'):<28} | {_('Category'):<20} | {_('Remaining'):<7}\n"

        output += "-" * 63 + "\n"
        comms:list = []
        qty:dict = {k: v - delivered[self.build_index].get(k, 0) for k, v in required[self.build_index].items()}
        if self.colonisation.docked == True and '$EXT_PANEL_ColonisationShip' not in f"{self.colonisation.station}" and 'Construction Site' not in f"{self.colonisation.station}":
            comms = self.colonisation.get_commodity_list(CommodityOrder.CATEGORY)
        else:
            comms = self.colonisation.get_commodity_list(self.comm_order, qty)

        for c in comms:
            reqcnt:int = required[self.build_index].get(c, 0) if len(required) > self.build_index else 0
            delcnt:int = delivered[self.build_index].get(c, 0) if len(delivered) > self.build_index else 0
            # Hide if we're docked and market doesn't have this.
            if not discord and self.colonisation.docked == True and self.colonisation.market != {} and self.colonisation.market.get(f"${c}_name;", 0) == 0:
                continue
            remaining:int = reqcnt - delcnt
            # Show amount left to buy unless it's our carrier in which case it needs to be amount left to deliver
            if not discord and self.colonisation.docked and self.colonisation.market_id != self.bgstally.fleet_carrier.carrier_id:
                remaining -= self.colonisation.cargo.get(c, 0)
                remaining -= self.colonisation.carrier_cargo.get(c, 0)

            if remaining > 0:
                name:str = self.colonisation.get_commodity(c, 'name')
                cat:str = self.colonisation.get_commodity(c, 'category')
                if discord:
                    output += f"{name:<28} | {cat:<20} | {remaining: 8,}{_('t')}\n"
                else:
                    output += f"{name}: {remaining}{_('t')}\n"

        if discord: output += "```\n"
        return output.strip()


    @catch_exceptions
    def event(self, event:str, tkEvent = None) -> None:
        ''' Process events from the buttons in the progress frame. '''
        tracked:dict = self.colonisation.get_tracked_builds()
        max:int = len(tracked) -1 if len(tracked) < 2 else len(tracked) # "All" if more than one build
        match event:
            case 'next':
                self.build_index += 1
                if self.build_index > max: self.build_index = 0
            case 'prev':
                self.build_index -= 1
                if self.build_index < 0: self.build_index = max
            case 'change':
                self.view = ProgressView((self.view.value + 1) % len(ProgressView))
                self.viewtt.text = _("Cycle commodity list details" + " (" + self.view.name.title()+")")
                self.colonisation.dirty = True
            case 'copy':
                self.frame.clipboard_clear()
                self.frame.clipboard_append(self.as_text())
            case _:
                self.frame.clipboard_clear()
                self.frame.clipboard_append(event)

        self.update_display()


    @catch_exceptions
    def change_view(self, column:int, which:str, tkEvent) -> None:
        ''' Change the view of the column when clicked. This cycles between tonnes, remaining, loads, etc. '''
        if column == 0:
            self.comm_order = CommodityOrder((self.comm_order.value + 1) % len(CommodityOrder))
            self.coltts[column].text = self.ordertts[self.comm_order.value]
        else:
            if which == 'Units':
                self.units[column] = ProgressUnits((self.units[column].value + 1) % (len(ProgressUnits)))
            else:
                val = (self.columns[column] + 1) % len(self.headings)
                if val == 0: val = 1 # Don't permit Commodities
                self.columns[column] = val
                self.coltts[column].text = self.headings[val].get('Tooltip')

        self.colonisation.dirty = True
        self.update_display()


    @catch_exceptions
    def link(self, comm:str, src:str|None, tkEvent) -> None:
        ''' Open the link to Inara for nearest location for the commodity. '''

        comm_id = self.bgstally.ui.commodities.get(comm, {}).get('InaraID', "")
        sys:str|None = self.colonisation.current_system if self.colonisation.current_system != None and src == None else src
        if sys == None: sys = 'sol'

        # pi3=3 - large, pi3=2 - medium
        size:int = 2 if self.colonisation.cargo_capacity < 407 else 3

        # pi7=5000 - supply (100, 500, 1000, 2500, 5000, 10000, 50000)
        tracked:dict = self.colonisation.get_tracked_builds()
        required:dict = self.colonisation.get_required(tracked)
        delivered:dict = self.colonisation.get_delivered(tracked)
        rem:int = (required[self.build_index].get(comm, 0) if len(required) > self.build_index else 0) - (delivered[self.build_index].get(comm, 0) if len(delivered) > self.build_index else 0)
        for min in [500, 1000, 2500, 5000, 10000, 50000]:
            if min > rem: break

        projectid:str|None = None
        if self.build_index < len(tracked):
            projectid = tracked[self.build_index].get('ProjectID', None)
        if self.build_index < len(tracked) and projectid == None:
            progress:dict = self.colonisation.find_progress(tracked[self.build_index].get('MarketID'))
            if progress != None:
                projectid = progress.get('ProjectID', None)

        # If we don't have a RavenColonial project ID then use Inara
        if projectid == None:
            url:str = f"https://inara.cz/elite/commodities/?formbrief=1&pi1=1&pa1[]={comm_id}&ps1={quote(sys)}&pi10=3&pi11=0&pi3={size}&pi9=0&pi4=0&pi14=0&pi5=720&pi12=0&pi7={min}&pi8=0&pi13=0"
            webbrowser.open(url)
            return

        url:str = f"https://ravencolonial100-awcbdvabgze4c5cq.canadacentral-01.azurewebsites.net/api/project/{projectid}/markets"
        payload:dict = {"refSystem": sys,
                        "shipSize": 'medium',
                        "requireNeed": True}
        self.bgstally.request_manager.queue_request(url, RequestMethod.POST, payload=payload, headers=RavenColonial(self.colonisation)._headers(), callback=self._markets_callback, attempts=3)

        # Create/recreate the frame now since it takes a while to show the data
        if self.mkts_fr != None and self.mkts_fr.winfo_exists(): self.mkts_fr.destroy()
        scale:float = config.get_int('ui_scale') / 100.00
        self.mkts_fr = tk.Toplevel(self.bgstally.ui.frame)
        self.mkts_fr.wm_title(_("{plugin_name} - Markets Window").format(plugin_name=self.bgstally.plugin_name)) # LANG: Title of the markets popup window
        width:int = sum([v.get('width') for v in self.markets.values()]) + 20
        self.mkts_fr.geometry(f"{int(width*scale)}x{int(500*scale)}")
        self.mkts_fr.protocol("WM_DELETE_WINDOW", self.mkts_fr.destroy)
        self.mkts_fr.config(bd=2, relief=tk.FLAT)


    @catch_exceptions
    def _markets_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Callback from the RavenColonial materials request to open popup '''
        if not self.mkts_fr or not self.mkts_fr.winfo_exists(): return

        if response == None or response.status_code != 200:
            Debug.logger.error(f"RavenColonial materials request failed")
            self.mkts_fr.destroy()
            return

        tmp:dict = response.json()
        markets:list = tmp.get('markets', [])
        if len(markets) == 0:
            Debug.logger.info("RavenColonial materials request returned no markets")
            self.mkts_fr.destroy()
            return

        scale:float = config.get_int('ui_scale') / 100.00
        header_fnt:tuple = (FONT_SMALL[0], FONT_SMALL[1], "bold")
        sheet:Sheet = Sheet(self.mkts_fr, sort_key=natural_sort_key, note_corners=True, show_row_index=False,
                        cell_auto_resize_enabled=True, height=4096,
                        show_horizontal_grid=True, show_vertical_grid=True, show_top_left=False,
                        align="center", show_selected_cells_border=True, table_selected_cells_border_fg='',
                        show_dropdown_borders=False, header_bg='lightgrey', header_selected_cells_bg='lightgrey',
                        empty_vertical=0, empty_horizontal=0, header_font=header_fnt, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                        show_header=True, default_row_height=int(19*scale), table_wrap="w", alternate_color="gray95")
        sheet.pack(fill=tk.BOTH, padx=0, pady=0)

        sheet.enable_bindings('single_select', 'column_select', 'row_select', 'drag_select', 'column_width_resize', 'right_click_popup_menu', 'copy', 'sort_rows')
        sheet.set_header_data([v['header'] for v in self.markets.values()])
        sheet.extra_bindings('cell_select', func=partial(self._sheet_clicked, sheet))

        tracked:dict = self.colonisation.get_tracked_builds()
        required:dict = self.colonisation.get_required(tracked)
        delivered:dict = self.colonisation.get_delivered(tracked)

        data:list = []
        for i, m in enumerate(list(k for k in sorted(markets, key=lambda item: item.get('distance'), reverse=False))):
            include:bool = False
            row:list = []
            for k, v in self.markets.items():
                d:str = ''
                match k:
                    case 'distance':
                        d = f"{m.get('distance', 0):,.1f}"
                    case 'distanceToArrival':
                        d = f"{int(m.get('distanceToArrival', 0)):,}"
                    case 'type':
                        d = 'S' if m.get('surface', False) == True else 'C' if m.get('type', '').lower().find('carrier') >= 0 else 'O'
                        sheet[f"E{i+1}"].highlight(bg=self.colors.get(d, 'white'))
                    case 'padSize':
                        d = m.get('padSize', '').upper()[0:1]
                        sheet[f"F{i+1}"].highlight(bg=self.colors.get(d, 'white'))
                    case 'count':
                        d = str(len([k for k, v in m.get('supplies', {}).items() if min(required[self.build_index].get(k, 0) - delivered[self.build_index].get(k, 0), v) > 0]))
                        if d != '0': include = True
                    case 'quantity':
                        d = f"{(sum([min(required[self.build_index].get(k, 0) - delivered[self.build_index].get(k, 0), v) for k, v in m.get('supplies', {}).items()])):,}"
                    case 'commodities':
                        # ⚠ ⊘ ⦵
                        d = ', '.join([f"{self.colonisation.get_commodity(k, 'name')} ({human_format(min(required[self.build_index].get(k, 0) - delivered[self.build_index].get(k, 0), v))}{'/'+human_format(required[self.build_index].get(k, 0) - delivered[self.build_index].get(k, 0)) if v < required[self.build_index].get(k, 0) - delivered[self.build_index].get(k, 0) else ''})" for k, v in m.get('supplies', {}).items() if min(required[self.build_index].get(k, 0) - delivered[self.build_index].get(k, 0), v) > 0])
                    case _:
                        d = m.get(k, '')
                row.append(d)

            if include == True:
                data.append(row)

        sheet.set_sheet_data(data, redraw=False)

        for i, (k, v) in enumerate(self.markets.items()):
            sheet.align_columns(i, v.get('align'))
            sheet.column_width(i, int(v.get('width')*scale))

        #sheet.set_all_column_widths(width=None, only_set_if_too_small=True, redraw=True, recreate_selection_boxes=True)
        sheet.set_all_row_heights(height=None, only_set_if_too_small=True, redraw=True)


    @catch_exceptions
    def _sheet_clicked(self, sheet:Sheet, event) -> None:
        ''' Open system or station '''
        #sheet.toggle_select_row(event.selected.row, False, True)
        if event.selected.column == 0:
            system:str = str(sheet[(event['selected'].row, event['selected'].column)].data)
            self.bgstally.ui.window_colonisation._link({'StarSystem': system}, 'System')


    @catch_exceptions
    def update_display(self) -> None:
        ''' Main display update function. '''
        tracked:list = self.colonisation.get_tracked_builds()
        required:list = self.colonisation.get_required(tracked)
        delivered:list = self.colonisation.get_delivered(tracked)

        if self.bgstally.state.enable_colonisation != True:
            self.frame.grid_remove()
            return

        if len(tracked) == 0 or self.colonisation.cargo_capacity < 8:
            self.frame.grid_remove()
            Debug.logger.info("No builds or commodities, hiding progress frame")
            return

        if self.build_index > len(required):
            Debug.logger.debug(f"Build index {self.build_index} out of range {len(tracked)}, resetting to 0")
            self.build_index = 0

        self.frame.grid()
        self.table_frame.grid()

        # Set the build name (system name and plan name)
        name = _('All') # LANG: all builds
        sn:str = _('Unknown') # LANG: Unknown system name
        if self.build_index < len(tracked):
            b:dict = tracked[self.build_index]
            bn:str = re.sub(r"(\w+ Construction Site:|\$EXT_PANEL_ColonisationShip;) ", "", b.get('Name', ''))
            bt:str = b.get('Base Type', '')
            pn:str = b.get('Plan', _('Unknown')) # Unknown system name
            sn:str = b.get('StarSystem', _('Unknown')) # Unknown system name
            name:str = ', '.join([pn, bt])
            if b.get('Name', '') != '':
                name = ', '.join([pn, bt, bn])
        self.titlett.text = f"{name}\n{_('left click to copy, right click menu')}" # LANG: tooltip for the build name"
        self.title.config(text=str_truncate(name, 52, loc='middle'))
        #self.title.config(foreground=config.get_str('dark_text') if config.get_int('theme') > 0 else 'black')

        # Hide the table but not the progress frame so the change view icon is still available
        if self.view == ProgressView.NONE:
            self.table_frame.grid_remove()
            Debug.logger.info("Progress view none, hiding table")
            return

        self.table_frame.grid()

        # Set the column headings according to the selected units
        for col, val in enumerate(self.columns):
            if val >= len(self.headings): val = len(self.headings) -1
            if col >= len(self.collbls): col = len(self.collbls) - 1
            if self.collbls[col] == None: col = 0
            self.collbls[col]['text'] = self.headings[val].get('Label')
            #self.collbls[col].config(foreground=config.get_str('dark_text') if config.get_int('theme') > 0 else 'black')
            self.collbls[col].grid()

        totals:dict = {'Commodity': _("Total"),  # LANG: total commodities
                        'Required': 0, 'Delivered': 0, 'Cargo' : 0, 'Carrier': 0, 'BuyOrder': 0}

        # Go through each commodity and show or hide it as appropriate and display the appropriate values
        comms:list = []
        if self.colonisation.docked == True and '$EXT_PANEL_ColonisationShip' not in f"{self.colonisation.station}" and 'Construction Site' not in f"{self.colonisation.station}":
            comms = self.colonisation.get_commodity_list(CommodityOrder.CATEGORY)
        else:
            if self.build_index >= len(required):
                comms = self.colonisation.get_commodity_list(self.comm_order)
            else:
                qty:dict = {k: v - delivered[self.build_index].get(k, 0) for k, v in required[self.build_index].items()}
                comms = self.colonisation.get_commodity_list(self.comm_order, qty)

        if comms == None or comms == []:
            Debug.logger.info(f"No commodities found")
            return

        rowcnt:int = 0
        for i, c in enumerate(comms):

            if i >= len(self.rows): continue
            row:dict = self.rows[i]
            reqcnt:int = required[self.build_index].get(c, 0) if len(required) > self.build_index else 0
            delcnt:int = delivered[self.build_index].get(c, 0) if len(delivered) > self.build_index else 0
            remaining:int = reqcnt - delcnt

            cargo:int = self.colonisation.cargo.get(c, 0)
            carrier:int = self.colonisation.carrier_cargo.get(c, 0)
            buyorder:int = self.colonisation.carrier_buy.get(c, 0)

            totals['Required'] += reqcnt
            totals['Delivered'] += delcnt

            # We only count relevant cargo not stuff we don't need.
            if reqcnt - delcnt > 0: totals['Cargo'] += max(min(cargo, reqcnt - delcnt), 0)
            if reqcnt - delcnt > 0: totals['Carrier'] += max(min(carrier, reqcnt - delcnt - cargo), 0)
            totals['BuyOrder'] += buyorder

            #if reqcnt > 0: Debug.logger.debug(f"Commodity {c}: Required {reqcnt}, Delivered {delcnt}, Remaining {remaining}, Cargo {cargo}, Carrier {carrier}")

            # We only show relevant (required) items. But.
            # If the view is reduced or minimal we don't show ones that are complete. Also.
            # If we're in minimal view we only show ones we still need to buy.
            docked:bool = self.colonisation.docked
            hasmarket:bool = self.colonisation.market != {}
            forsale:bool = self.colonisation.market.get(f"${c}_name;", 0) > 0
            atcarrier:bool = self.colonisation.market_id == self.bgstally.fleet_carrier.carrier_id
            needtobuy:bool = remaining - carrier - cargo > 0
            if (reqcnt <= 0) or \
                ((rowcnt > int(self.bgstally.state.ColonisationMaxCommodities.get()) > 0) and \
                 self.bgstally.state.EnableProgressScrollbar.get() == CheckStates.STATE_OFF) or \
                (remaining <= 0 and cargo == 0 and self.view != ProgressView.FULL) or \
                (docked and not forsale and not needtobuy and cargo == 0 and self.view == ProgressView.REDUCED) or \
                ((not docked or not hasmarket) and not needtobuy and cargo == 0 and self.view == ProgressView.MINIMAL) or \
                (docked and not forsale and cargo == 0 and self.view == ProgressView.MINIMAL) or \
                (docked and not atcarrier and not needtobuy and cargo == 0 and self.view == ProgressView.MINIMAL):
                for cell in row.values():
                    cell.grid_remove()
                continue

            if rowcnt == int(self.bgstally.state.ColonisationMaxCommodities.get()) and self.bgstally.state.EnableProgressScrollbar.get() == CheckStates.STATE_OFF:
                for cell in row.values():
                    cell['text'] = '… '
                    cell.grid()
                rowcnt += 1
                continue

            for col, val in enumerate(self.columns):
                row[col].bind("<Button-1>", partial(self.link, c, None))
                row[col].bind("<Button-2>", partial(self.link, c, sn))
                row[col].bind("<Button-3>", partial(self.event, self.colonisation.get_commodity(c)))

                if col == 0:
                    # Shorten and display the commodity name
                    row[col]['text'] = str_truncate(self.colonisation.get_commodity(c), 23)
                    row[col].grid()
                    continue

                row[col]['text'] = self._get_value(col, reqcnt, delcnt, cargo, carrier, buyorder)
                row[col].grid()

            self._highlight_row(row, c, reqcnt, delcnt, cargo, carrier)
            rowcnt += 1

        self._display_totals(self.rows[i+1], tracked, totals)

        if self.bgstally.state.EnableProgressScrollbar.get() == CheckStates.STATE_ON:
            Debug.logger.debug(f"Resizing Cnvas: {self.bgstally.state.EnableProgressScrollbar.get()} {rowcnt < int(self.bgstally.state.ColonisationMaxCommodities.get())}")
            rows = min(rowcnt, int(self.bgstally.state.ColonisationMaxCommodities.get()))
            self.scroll_canvas.yview_moveto(0.0)
            height=int((rows+2)*21*(config.get_int('ui_scale') / 100.00))
            self.scroll_canvas.configure(height=height)

        if totals['Required'] > 0:
            self.progvar.set(round(totals['Delivered'] * 100 / totals['Required']))
            self.progress = round(totals['Delivered'] * 100 / totals['Required'])
            self.progtt.text = f"{_('Progress')}: {int(self.progvar.get())}%" # LANG: tooltip for the progress bar


    @catch_exceptions
    def _display_totals(self, row:dict, tracked:list, totals:dict) -> None:
        ''' Display the totals at the bottom of the table '''

        # We're down to having nothing left to deliver.
        if (totals['Required'] - totals['Delivered']) == 0:
            if len(tracked) == 0: # Nothing at all, remove the entire frame
                self.frame.grid_remove()
            else: # Just this one build? Hide the table
                self.table_frame.grid_remove()
            return

        for col, val in enumerate(self.columns):
            row[col]['text'] = self._get_value(col, totals['Required'], totals['Delivered'], totals.get('Cargo',0), totals.get('Carrier', 0), totals.get('BuyOrder', 0)) if col != 0 else _("Total")
            self._set_weight(row[col])
            row[col].grid()


    @catch_exceptions
    def _get_value(self, col:int, required:int, delivered:int, cargo:int, carrier:int, buyorder:int) -> str:
        ''' Calculate and format the commodity amount depending on the column and the units '''
        qty: int = 0
        if col >= len(self.columns):
            Debug.logger.debug(f"Col: {col} {self.columns}")
            return ""
        if self.columns[col] >= len(self.headings):
            Debug.logger.debug(f"heading: {self.columns[col]} {self.headings}")
            return ""

        which:str = self.headings[self.columns[col]].get('Column')
        match which:
            case 'Required': qty = required
            case 'Remaining': qty = required - delivered
            case 'Delivered': qty = delivered
            case 'Purchase': qty = required - delivered-cargo-carrier
            case 'Cargo': qty = cargo
            case 'Carrier': qty = carrier
            case 'BuyOrder': qty = buyorder

        qty = max(qty, 0) # Never less than zero
        if self.units[col] == ProgressUnits.LOADS and ceil(qty / self.colonisation.cargo_capacity) > 1:
            return f"{ceil(qty / self.colonisation.cargo_capacity): >10,}{_('L')}"

        return f"{qty: >10,}{_('t')}"


    def _set_weight(self, cell, w='bold') -> None:
        ''' Set font weight, defaults to bold '''
        fnt:tkFont._FontDict = tkFont.Font(font=cell['font']).actual()
        cell.configure(font=(fnt['family'], fnt['size'], w))


    @catch_exceptions
    def _highlight_row(self, row:dict, c:str, required:int, delivered:int, cargo:int, carrier:int) -> None:
        ''' Color rows depending on the state '''
        remaining:int = required - delivered
        space:int = self.colonisation.cargo_capacity - sum(self.colonisation.cargo.values())
        for cell in row.values():
            # Get the ed:mc default color
            #cell['fg'] = config.get_str('dark_text') if config.get_int('theme') > 0 else 'black'
            self._set_weight(cell, 'normal')

            if remaining <= 0: # Nothing left to deliver, grey it out
                cell['fg'] = 'grey'; self._set_weight(cell, 'normal')
                continue

            if remaining <= cargo: # Have enough in our hold? green and bold
                cell['fg'] = 'green'; self._set_weight(cell, 'bold')
                continue

            # We're at our carrier, highlight what's available
            if self.colonisation.docked == True and self.colonisation.market_id == self.bgstally.fleet_carrier.carrier_id and self.colonisation.market.get(f"${c}_name;", 0) > 0:
                cell['fg'] = 'goldenrod3'
                # bold if need any and have room, otherwise normal
                self._set_weight(cell, 'bold' if remaining-cargo-carrier <= 0 and space > 0 else 'normal')
                continue

            if remaining <= cargo+carrier : # Have enough between our hold and the carrier? green and normal
                cell['fg'] = 'green'; self._set_weight(cell, 'normal')
                continue

            # What's available at this market?
            if self.colonisation.docked == True and self.colonisation.market.get(f"${c}_name;", 0): # market!
                cell['fg'] = 'steelblue'
                # bold if need any and have room, otherwise normal
                self._set_weight(cell, 'bold' if remaining-cargo-carrier > 0 and space > 0 else 'normal')
                continue
