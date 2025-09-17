import tkinter as tk
import tkinter.font as tkFont
import webbrowser
import re
import requests
from requests import Response
from functools import partial
from math import ceil
from tkinter import ttk
from urllib.parse import quote

from bgstally.constants import TAG_OVERLAY_HIGHLIGHT, FONT_SMALL, RequestMethod, CommodityOrder, ProgressUnits, ProgressView
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
                'Label' : f"{_('Commodity'): <24}", # LANG: Commodity
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
            }
        ]
        self.ordertts:list = [_('Alphabetical order'), _('Category order'), _('Quantity order')]

        self.markets:dict = {
            'systemName' : {'Header': _('System'), 'Width': 175, 'Align': "left"},      # LANG: System Name heading
            'stationName' : {'Header': _('Station'), 'Width': 175, 'Align': "left"},    # LANG: Station name heading
            'distance': {'Header': _('Distance (ly)'), 'Width': 75, 'Align': "center"}, # LANG: System distance heading
            'distanceToArrival': {'Header': _('Arrival (ls)'), 'Width': 75, 'Align': "center"}, # LANG: station distance from arrival heading
            'type': {'Header': _('Type'), 'Width': 35, 'Align': "center"},              # LANG: Station type (O=Orbital, S=Surface, C=Carrier)
            'padSize': {'Header': _('Pad'), 'Width': 35, 'Align': "center"},            # LANG: Pad size (L, M, S)
            'count': {'Header': _('Count'), 'Width':45, 'Align': "center"},             # LANG: Count of commodities available
            'commodities': {'Header': _('Commodities'), 'Width': 515, 'Align': "left"}  # LANG: List of commodities available
            }

        self.colors:dict = {'L' : '#d4edbc', 'M' : '#dbe5ff', 'O' : '#d5deeb', 'S' : '#ebe6db', 'C' : '#e6dbeb'}

        # Initialise the default units & column types
        self.units:list = [CommodityOrder.ALPHA, ProgressUnits.QTY, ProgressUnits.QTY, ProgressUnits.QTY]
        self.columns:list = [0, 2, 3, 5]
        self.collbls:list = [None, None, None, None] # Column headings
        self.coltts: list = [None, None, None, None]

        # By removing the carrier from here we remove it everywhere
        if not self.bgstally.fleet_carrier.available():
            self.headings = self.headings.pop()

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
        self.build_index:int = 0 # Which build we're showing
        self.view:ProgressView = ProgressView.REDUCED # Full, reduced, or no list of commodities
        self.comm_order:CommodityOrder = CommodityOrder.ALPHA # Commodity order


    @catch_exceptions
    def create_frame(self, parent_frame:tk.Frame, start_row:int, column_count:int) -> None:
        ''' Create the progress frame. This is called by ui.py on startup. '''
        self.colonisation = self.bgstally.colonisation
        tracked:dict = self.colonisation.get_tracked_builds()

        self.frame_row = start_row
        frame:tk.Frame = tk.Frame(parent_frame)
        frame.grid(row=start_row, column=0, columnspan=20, sticky=tk.EW)
        self.frame = frame

        row:int = 0; col:int = 0

        # Overall progress bar chart
        y=tk.LabelFrame(frame, border=1, height=10)
        y.grid(row=row, column=col, columnspan=5, pady=0, sticky=tk.EW)
        y.grid_rowconfigure(0, weight=1)
        y.grid_propagate(False)
        self.progbar:ttk.Progressbar = ttk.Progressbar(y, orient=tk.HORIZONTAL, variable=self.progvar, maximum=100, length=450, mode='determinate')
        self.progtt:ToolTip = ToolTip(self.progbar, text=_("Progress")) # LANG: progress tooltip
        self.progbar.grid(row=0, column=0, columnspan=20, pady=0, ipady=0, sticky=tk.EW)
        self.progbar.rowconfigure(0, weight=1)
        row += 1; col = 0
        lbl:tk.Label = tk.Label(frame, text=_("Builds") + ":", anchor=tk.W) # LANG: Builds/bases
        lbl.grid(row=row, column=0, sticky=tk.W)
        self._set_weight(lbl)
        col += 1

        self.title = tk.Label(frame, text=_("None"), justify=tk.CENTER, anchor=tk.CENTER, cursor="hand2") # LANG: None
        self.title.config(foreground=config.get_str('dark_text') if config.get_int('theme') == 1 else 'black')
        self.title.bind("<Button-1>", partial(self.event, "copy"))
        self.title.grid(row=row, column=col, sticky=tk.EW)
        frame.columnconfigure(col, weight=1)
        self.titlett:ToolTip = ToolTip(self.title, text=f"{_('Current build')}, {_('click to copy to clipboard')}") # LANG: tooltip for the build name
        col += 1

        prev_btn:tk.Label = tk.Label(frame, image=self.bgstally.ui.image_icon_left_arrow, cursor="hand2")
        prev_btn.bind("<Button-1>", partial(self.event, "prev"))
        prev_btn.grid(row=row, column=col, sticky=tk.W)
        ToolTip(prev_btn, text=_("Show previous build")) # LANG: tooltip for the previous build icon
        col += 1

        view_btn:tk.Label = tk.Label(frame, image=self.bgstally.ui.image_icon_change_view, cursor="hand2")
        view_btn.bind("<Button-1>", partial(self.event, "change"))
        view_btn.grid(row=row, column=col, sticky=tk.E)
        ToolTip(view_btn, text=_("Cycle commodity list details")) # LANG: tooltip for the commodity header
        col += 1

        next_btn:tk.Label = tk.Label(frame, image=self.bgstally.ui.image_icon_right_arrow, cursor="hand2")
        next_btn.bind("<Button-1>", partial(self.event, "next"))
        next_btn.grid(row=row, column=col, sticky=tk.E)
        ToolTip(next_btn, text=_("Show next build")) # LANG: tooltip for the next build icon
        row += 1; col = 0

        # Commodity frame
        table_frame:tk.Frame = tk.Frame(frame)
        table_frame.columnconfigure(0, weight=3)
        table_frame.columnconfigure(1, weight=1)
        table_frame.columnconfigure(2, weight=1)
        table_frame.grid(row=row, column=col, columnspan=5, sticky=tk.NSEW)
        self.table_frame = table_frame

        # Column headings
        row = 0
        for col, v in enumerate(self.columns):
            lbl = tk.Label(table_frame, text=self.headings[v].get('Label'), cursor='hand2')
            lbl.bind("<Button-1>", partial(self.change_view, col, 'Column'))
            lbl.bind("<Button-3>", partial(self.change_view, col, 'Units'))

            lbl.config(foreground=config.get_str('dark_text') if config.get_int('theme') == 1 else 'black')
            self._set_weight(lbl)
            lbl.grid(row=row, column=col, sticky=tk.W if col == 0 else tk.E, padx=(0,5))

            self.collbls[col] = lbl
            self.coltts[col] = ToolTip(lbl, text=self.headings[v].get('Tooltip'))
        row += 1

        # Go through the complete list of possible commodities and make a row for each and hide it.
        for c in self.colonisation.get_commodity_list():
            r:dict = {}

            for col, v in enumerate(self.columns):
                lbl:tk.Label = tk.Label(table_frame, text='', cursor="hand2")
                lbl.config(foreground=config.get_str('dark_text') if config.get_int('theme') == 1 else 'black')
                lbl.grid(row=row, column=col, sticky=tk.W if col == 0 else tk.E, padx=(0,5))
                if row == 0:
                    lbl.bind("<Button-1>", partial(self.link, c, None))
                    lbl.bind("<Button-3>", partial(self.ctc, self.colonisation.get_commodity(c)))
                    ToolTip(lbl, text=_("Left click for Inara market, right click to copy")) # LANG: tooltip for the inara market commodity links and copy to clipboard
                    lbl.config(cursor='hand2', foreground=config.get_str('dark_text') if config.get_int('theme') == 1 else 'black')

                r[col] = lbl
            self.rows.append(r)
            row += 1

        # Totals at the bottom
        r:dict = {}
        for col, v in enumerate(self.columns):
            r[col] = tk.Label(table_frame, text=_("Total")) # LANG: Total amounts
            r[col].grid(row=row, column=col, sticky=tk.W if col == 0 else tk.E, padx=(0,5))
            self._set_weight(r[col])

        self.rows.append(r)

        # No builds or no commodities so hide the frame entirely
        if len(tracked) == 0 or len(self.colonisation.get_required(tracked)) == 0:
            Debug.logger.info("No builds or commodities, hiding progress frame")
            frame.grid_remove()
            return

        self.update_display()


    @catch_exceptions
    def as_text(self, discord:bool = True) -> str:
        ''' Return a text representation of the progress window '''
        if not hasattr(self.bgstally, 'colonisation'):
            return _("No colonisation data available") # LANG: No colonisation data available
        self.colonisation = self.bgstally.colonisation

        output:str = ""
        tracked:list = self.colonisation.get_tracked_builds()
        required:dict = self.colonisation.get_required(tracked)
        delivered:dict = self.colonisation.get_delivered(tracked)

        if self.build_index < len(tracked):
            b:dict = tracked[self.build_index]
            sn:str = b.get('Plan', _('Unknown')) # Unknown system name
            bn:str = b.get('Name', '') if b.get('Name','') != '' else b.get('Base Type', '')
            if discord:
                output += f"```{sn}, {bn}\n"
            else:
                output += f"{TAG_OVERLAY_HIGHLIGHT}{sn}\n{TAG_OVERLAY_HIGHLIGHT}{str_truncate(bn, 30, loc='left')}\n"
        else:
            if discord:
                output += "```" + _("All builds") + "\n" # LANG: all tracked builds
            else:
                output += TAG_OVERLAY_HIGHLIGHT + _("All builds") + "\n" # LANG: all tracked builds

        output += f"{_('Progress')}: {self.progvar.get():.0f}%\n"
        output += "\n"
        if discord:
            output += f"{_('Commodity'):<28} | {_('Category'):<20} | {_('Remaining'):<7} |\n"

        output += "-" * 67 + "\n"

        for c in self.colonisation.get_commodity_list(CommodityOrder.CATEGORY):
            reqcnt:int = required[self.build_index].get(c, 0) if len(required) > self.build_index else 0
            delcnt:int = delivered[self.build_index].get(c, 0) if len(delivered) > self.build_index else 0
            # Hide if we're docked and market doesn't have this.
            if not discord and self.colonisation.docked == True and self.colonisation.market != {} and self.colonisation.market.get(c, 0) == 0:
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
                    output += f"{name:<28} | {cat:<20} | {remaining: 7,} {_('t')} |\n"
                else:
                    output += f"{name}: {remaining} {_('t')}\n"

        if discord: output += "```\n"
        return output.strip()


    @catch_exceptions
    def event(self, event:str, tkEvent) -> None:
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
                self.colonisation.dirty = True
            case 'copy':
                self.title.clipboard_clear()
                self.title.clipboard_append(self.as_text())
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
        self.colonisation.dirty = True
        self.update_display()


    @catch_exceptions
    def link(self, comm:str, src:str|None, tkEvent) -> None:
        ''' Open the link to Inara for nearest location for the commodity. '''

        comm_id = self.colonisation.base_types['InaraIDs'].get(comm)
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

        # If we don't have a single build then use Inara
        if self.build_index >= len(tracked):
            url:str = f"https://inara.cz/elite/commodities/?formbrief=1&pi1=1&pa1[]={comm_id}&ps1={quote(sys)}&pi10=3&pi11=0&pi3={size}&pi9=0&pi4=0&pi14=0&pi5=720&pi12=0&pi7={min}&pi8=0&pi13=0"
            webbrowser.open(url)

        projectid:str = tracked[self.build_index].get('ProjectID', '')
        if projectid == '':
            progress:dict = self.colonisation.find_progress(tracked[self.build_index].get('MarketID'))
            if progress != None:
                projectid = progress.get('ProjectID', '')

        # If we don't have a RavenColonial project ID then use Inara
        if projectid == '':
            url:str = f"https://inara.cz/elite/commodities/?formbrief=1&pi1=1&pa1[]={comm_id}&ps1={quote(sys)}&pi10=3&pi11=0&pi3={size}&pi9=0&pi4=0&pi14=0&pi5=720&pi12=0&pi7={min}&pi8=0&pi13=0"
            webbrowser.open(url)

        url:str = f"https://ravencolonial100-awcbdvabgze4c5cq.canadacentral-01.azurewebsites.net/api/project/{projectid}/markets"
        payload:dict = {"systemName": sys,
                        "shipSize": 'medium',
                        "requireNeed": True}
        self.bgstally.request_manager.queue_request(url, RequestMethod.POST, payload=payload, headers=RavenColonial(self.colonisation)._headers(), callback=self._markets_callback)

        # Create/recreate the frame now since it takes a while to show the data
        if self.mkts_fr != None and self.mkts_fr.winfo_exists(): self.mkts_fr.destroy()
        scale:float = config.get_int('ui_scale') / 100.00
        self.mkts_fr = tk.Toplevel(self.bgstally.ui.frame)
        self.mkts_fr.wm_title(_("{plugin_name} - Markets Window").format(plugin_name=self.bgstally.plugin_name)) # LANG: Title of the markets popup window
        width:int = sum([v.get('Width') for v in self.markets.values()]) + 20
        self.mkts_fr.geometry(f"{int(width*scale)}x{int(500*scale)}")
        self.mkts_fr.protocol("WM_DELETE_WINDOW", self.mkts_fr.destroy)
        self.mkts_fr.config(bd=2, relief=tk.FLAT)


    @catch_exceptions
    def _markets_callback(self, success:bool, response:Response, request:BGSTallyRequest) -> None:
        ''' Callback from the RavenColonial materials request to open popup '''
        if response.status_code != 200:
            Debug.logger.error(f"RavenColonial materials request failed: {response.status_code} {response.text}")
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
        sheet:Sheet = Sheet(self.mkts_fr, sort_key=natural_sort_key, note_corners=True, show_row_index=False, cell_auto_resize_enabled=True, height=4096,
                        show_horizontal_grid=True, show_vertical_grid=True, show_top_left=False,
                        align="center", show_selected_cells_border=True, table_selected_cells_border_fg='',
                        show_dropdown_borders=False, header_bg='lightgrey', header_selected_cells_bg='lightgrey',
                        empty_vertical=0, empty_horizontal=0, header_font=header_fnt, font=FONT_SMALL, arrow_key_down_right_scroll_page=True,
                        show_header=True, default_row_height=int(19*scale), table_wrap="w", alternate_color="gray95")
        sheet.pack(fill=tk.BOTH, padx=0, pady=0)

        sheet.enable_bindings('single_select', 'column_select', 'row_select', 'drag_select', 'column_width_resize', 'right_click_popup_menu', 'copy', 'sort_rows')
        sheet.set_header_data([v['Header'] for v in self.markets.values()])
        sheet.extra_bindings('cell_select', func=partial(self._sheet_clicked, sheet))

        tracked:dict = self.colonisation.get_tracked_builds()
        required:dict = self.colonisation.get_required(tracked)
        delivered:dict = self.colonisation.get_delivered(tracked)

        data:list = []
        for i, m in enumerate(list(k for k in sorted(markets, key=lambda item: item.get('distance'), reverse=False))):
            row:list = []
            for k, v in self.markets.items():
                d:str = ''
                match k:
                    case 'type':
                        d = 'S' if m.get('surface', False) == True else 'C' if m.get('type', '').lower().find('carrier') >= 0 else 'O'
                        sheet[f"E{i+1}"].highlight(bg=self.colors.get(d, 'white'))
                    case 'count':
                        d = str(len([f"{self.colonisation.get_commodity(k, 'name')} ({human_format(v)})" for k, v in m.get('supplies', {}).items() if 0 < required[self.build_index].get(k, 0) - delivered[self.build_index].get(k, 0) < v]))
                    case 'padSize':
                        d = m.get('padSize', '').upper()[0:1]
                        sheet[f"F{i+1}"].highlight(bg=self.colors.get(d, 'white'))
                    case 'commodities':
                        d = ', '.join([f"{self.colonisation.get_commodity(k, 'name')} ({human_format(v)})" for k, v in m.get('supplies', {}).items() if 0 < required[self.build_index].get(k, 0) - delivered[self.build_index].get(k, 0) < v])
                    case 'distance' | 'distanceToArrival':
                        d = f"{m.get('distance', 0):,.1f}"
                    case 'distanceToArrival':
                        d = f"{int(m.get('distanceToArrival', 0)):,}"
                    case _:
                        d = m.get(k, '')
                row.append(d)
            data.append(row)

        sheet.set_sheet_data(data)

        for i, (k, v) in enumerate(self.markets.items()):
            sheet.align_columns(i, v.get('Align'))
            sheet.column_width(i, int(v.get('Width')*scale))

        #self.msheet.set_all_column_widths(width=None, only_set_if_too_small=True, redraw=True, recreate_selection_boxes=True)
        sheet.set_all_row_heights(height=None, only_set_if_too_small=True, redraw=True)


    @catch_exceptions
    def _sheet_clicked(self, sheet:Sheet, event) -> None:
        ''' Open system or station '''
        #sheet.toggle_select_row(event.selected.row, False, True)
        if event.selected.column == 0:
            system:str = str(sheet[(event['selected'].row, event['selected'].column)].data)
            self.bgstally.ui.window_colonisation._link({'StarSystem': system}, 'System')


    def ctc(self, comm:str, event) -> None:
        ''' Copy to clipboard '''
        self.frame.clipboard_clear()
        self.frame.clipboard_append(comm)


    @catch_exceptions
    def update_display(self) -> None:
        ''' Main display update function. '''
        tracked:list = self.colonisation.get_tracked_builds()
        required:dict = self.colonisation.get_required(tracked)
        delivered:dict = self.colonisation.get_delivered(tracked)

        if len(tracked) == 0 or self.colonisation.cargo_capacity < 8:
            self.frame.grid_remove()
            Debug.logger.info("No builds or commodities, hiding progress frame")
            return

        self.frame.grid(row=self.frame_row, column=0, columnspan=20, sticky=tk.EW)
        self.table_frame.grid(row=3, column=0, columnspan=5, sticky=tk.NSEW)

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
        self.titlett.text = f"{name}, {_('click to copy to clipboard')}"
        self.title.config(text=str_truncate(name, 52, loc='middle'))

        # Hide the table but not the progress frame so the change view icon is still available
        if self.view == ProgressView.NONE:
            self.table_frame.grid_remove()
            Debug.logger.info("Progress view none, hiding table")
            return

        self.table_frame.grid(row=3, column=0, columnspan=5, sticky=tk.NSEW)

        # Set the column headings according to the selected units
        for col, val in enumerate(self.columns):
            self.collbls[col]['text'] = self.headings[val].get('Label')
            self.collbls[col].grid()

        totals:dict = {'Commodity': _("Total"),  # LANG: total commodities
                        'Required': 0, 'Delivered': 0, 'Cargo' : 0, 'Carrier': 0}

        # Go through each commodity and show or hide it as appropriate and display the appropriate values
        comms:list = []
        qty:dict = {k: v - delivered[self.build_index].get(k, 0) for k, v in required[self.build_index].items()}
        if self.colonisation.docked == True:
            comms = self.colonisation.get_commodity_list(CommodityOrder.CATEGORY)
        else:
            comms = self.colonisation.get_commodity_list(self.comm_order, qty)

        if comms == None or comms == []:
            Debug.logger.info(f"No commodities found")
            return

        rc:int = 0
        for i, c in enumerate(comms):
            if len(self.rows) < i: continue
            row:dict = self.rows[i]
            reqcnt:int = required[self.build_index].get(c, 0) if len(required) > self.build_index else 0
            delcnt:int = delivered[self.build_index].get(c, 0) if len(delivered) > self.build_index else 0
            remaining:int = reqcnt - delcnt

            cargo:int = self.colonisation.cargo.get(c, 0)
            carrier:int = self.colonisation.carrier_cargo.get(c, 0)

            totals['Required'] += reqcnt
            totals['Delivered'] += delcnt

            # We only count relevant cargo not stuff we don't need.
            if reqcnt - delcnt > 0: totals['Cargo'] += max(min(cargo, reqcnt - delcnt), 0)
            if reqcnt - delcnt > 0: totals['Carrier'] += max(min(carrier, reqcnt - delcnt - cargo), 0)

            # We only show relevant (required) items. But.
            # If the view is reduced or minimal we don't show ones that are complete. Also.
            # If we're in minimal view we only show ones we still need to buy.
            #Debug.logger.debug(f"{c} {remaining - carrier - cargo} {cargo} {self.view}")
            if (reqcnt <= 0) or \
                (remaining <= 0 and cargo == 0 and self.view != ProgressView.FULL) or \
                ((self.colonisation.docked == False or self.colonisation.market == {}) and remaining - carrier - cargo <= 0 and cargo == 0 and self.view == ProgressView.MINIMAL) or \
                (self.colonisation.docked == True and self.colonisation.market != {} and self.colonisation.market.get(c, 0) <= 0 and self.view == ProgressView.MINIMAL) or \
                rc > int(self.bgstally.state.ColonisationMaxCommodities.get()):
                for cell in row.values():
                    cell.grid_remove()
                continue

            if rc == int(self.bgstally.state.ColonisationMaxCommodities.get()):
                for cell in row.values():
                    cell['text'] = '… '
                    cell.grid()
                rc += 1
                continue

            for col, val in enumerate(self.columns):
                row[col].bind("<Button-1>", partial(self.link, c, None))
                row[col].bind("<Button-2>", partial(self.link, c, sn))
                row[col].bind("<Button-3>", partial(self.ctc, self.colonisation.get_commodity(c)))

                if col == 0:
                    # Shorten and display the commodity name
                    row[col]['text'] = str_truncate(self.colonisation.get_commodity(c), 24)
                    row[col].grid()
                    continue

                row[col]['text'] = self._get_value(col, reqcnt, delcnt, cargo, carrier)
                row[col].grid()

            self._highlight_row(row, c, reqcnt, delcnt, cargo, carrier)
            rc += 1

        self._display_totals(self.rows[i+1], tracked, totals)
        if totals['Required'] > 0:
            self.progvar.set(round(totals['Delivered'] * 100 / totals['Required']))
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
            row[col]['text'] = self._get_value(col, totals['Required'], totals['Delivered'], totals.get('Cargo',0), totals.get('Carrier', 0)) if col != 0 else _("Total")
            self._set_weight(row[col])
            row[col].grid()


    @catch_exceptions
    def _get_value(self, col:int, required:int, delivered:int, cargo:int, carrier:int) -> str:
        ''' Calculate and format the commodity amount depending on the column and the units '''
        qty: int = 0
        which:str = self.headings[self.columns[col]].get('Column')
        match which:
            case 'Required': qty = required
            case 'Remaining': qty = required - delivered
            case 'Delivered': qty = delivered
            case 'Purchase': qty = required - delivered-cargo-carrier
            case 'Cargo': qty = cargo
            case 'Carrier': qty = carrier
        qty = max(qty, 0) # Never less than zero
        if self.units[col] == ProgressUnits.LOADS and ceil(qty / self.colonisation.cargo_capacity) > 1:
            return f"{ceil(qty / self.colonisation.cargo_capacity): >12,}{_('L')}"

        return f"{qty: >12,}{_('t')}"


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
            cell['fg'] = config.get_str('dark_text') if config.get_int('theme') == 1 else 'black'
            self._set_weight(cell, 'normal')

            if remaining <= 0: # Nothing left to deliver, grey it out
                cell['fg'] = 'grey'; self._set_weight(cell, 'normal')
                continue

            if remaining <= cargo: # Have enough in our hold? green and bold
                cell['fg'] = 'green'; self._set_weight(cell, 'bold')
                continue

            # We're at our carrier, highlight what's available
            if self.colonisation.docked == True and self.colonisation.market_id == self.bgstally.fleet_carrier.carrier_id and self.colonisation.market.get(c, 0) > 0:
                cell['fg'] = 'goldenrod3'
                # bold if need any and have room, otherwise normal
                self._set_weight(cell, 'bold' if remaining-cargo-carrier <= 0 and space > 0 else 'normal')
                continue

            if remaining <= cargo+carrier : # Have enough between our hold and the carrier? green and normal
                cell['fg'] = 'green'; self._set_weight(cell, 'normal')
                continue

            # What's available at this market?
            if self.colonisation.docked == True and self.colonisation.market.get(c, 0): # market!
                cell['fg'] = 'steelblue'
                # bold if need any and have room, otherwise normal
                self._set_weight(cell, 'bold' if remaining-cargo-carrier > 0 and space > 0 else 'normal')
                continue
