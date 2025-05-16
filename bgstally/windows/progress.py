import traceback
import tkinter as tk
import tkinter.font as tkFont
from math import ceil
from tkinter import ttk
from enum import Enum, auto
from functools import partial
import webbrowser
from bgstally.constants import CommodityOrder

from bgstally.debug import Debug
from bgstally.utils import _

class View(Enum):
    FULL = 0
    REDUCED = auto()

class Units(Enum):
    TONNES = 0
    REMAINING = auto()
    LOADS = auto()
    PERCENT = auto()

MAX_ROWS = 35

#@TODO: replace f"{}:," with string_from_number()
class ProgressWindow:
    """
    Window for displaying construction progress for Elite Dangerous colonisation
    """
    def __init__(self, bgstally):
        """
        Initialize the progress window

        Args:
            parent: The parent window
            colonisation: The Colonisation instance
            state: The BGSTally state
        """
        self.bgstally = bgstally
        self.colonisation = None

        self.units:dict = {'Commodity': Units.TONNES, 'Required': Units.TONNES, 'Delivered':Units.TONNES, 'Cargo':Units.TONNES, 'Carrier': Units.TONNES}

        self.headings:dict = {
            'Commodity': {
                Units.TONNES: f"{_('Commodity'):<11}", # LANG: Commodity
                Units.REMAINING: f"{_('Commodity'):<11}",
                Units.PERCENT: f"{_('Commodity'):<11}",
                Units.LOADS: f"{_('Commodity'):<11}",
                'Sticky': tk.W
                },
            'Required': {
                Units.TONNES: f"{_('Required'):>10}", # LANG: Required amount
                Units.REMAINING: f"{_('Needed'):>10}", # LANG: Amount still needed
                Units.PERCENT: f"{_('Percent'):>11}", # LANG: Percentage
                Units.LOADS: f"{_('Loads'):>12}", # LANG: number of cargo loads
                'Sticky': tk.E
                },
            'Delivered': {
                Units.TONNES: f"{_('Delivered'):>10}", # LANG: Amount delivered
                Units.REMAINING: f"{_('To Buy'):>11}", # LANG: Amount still left to buy
                Units.PERCENT: f"{_('Percent'):>11}",
                Units.LOADS: f"{_('Loads'):>12}",
                'Sticky': tk.E
                },
            'Cargo': {
                Units.TONNES: f"{_('Cargo'):>1}", # LANG: amount in ship's Cargo
                Units.REMAINING: f"{_('Needed'):>9}",
                Units.PERCENT: f"{_('Percent'):>11}",
                Units.LOADS: f"{_('Loads'):>12}",
                'Sticky': tk.E
                },
            'Carrier': {
                Units.TONNES: f"{_('Carrier'):>11}", # LANG: Amount in your Fleet Carrier
                Units.REMAINING: f"{_('Needed'):>9}",
                Units.PERCENT: f"{_('Percent'):>11}",
                Units.LOADS: f"{_('Loads'):>12}",
                'Sticky': tk.E
                }
            }

        # UI components
        self.frame:tk.Frame = None
        self.frame_row:int = 0 # Row in the parent frame
        self.table_frame:tk.Frame = None # Table frame
        self.title:tk.Label = None # Title object
        self.colheadings:dict = {} # Column headings
        self.rows:list = []
        self.progcols:dict = {} # Progress bar variables
        self.build_index:int = 0 # Which build we're showing
        self.view:View = View.REDUCED # Full or reduced list of commodities
        self.comm_order:CommodityOrder = CommodityOrder.DEFAULT # Commodity order

    def create_frame(self, parent_frame:tk.Frame, start_row:int, column_count:int) -> None:
        """
        Create the progress frame
        """
        try:
            self.colonisation = self.bgstally.colonisation
            tracked:dict = self.colonisation.get_tracked_builds()

            self.frame_row = start_row
            frame:tk.Frame = tk.Frame(parent_frame)
            frame.grid(row=start_row, column=0, columnspan=20, sticky=tk.EW)
            self.frame = frame

            row:int = 0; col:int = 0
            ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=5, pady=2, sticky=tk.EW)
            row += 1

            lbl:tk.Label = tk.Label(frame, text=_("Builds") + ":", anchor=tk.W) # LANG: Builds/bases
            lbl.grid(row=row, column=0, sticky=tk.W)
            self.weight(lbl)
            col += 1

            self.title = tk.Label(frame, text=_("None"), justify=tk.CENTER, anchor=tk.CENTER) # LANG: None
            self.title.grid(row=row, column=col, sticky=tk.EW)
            frame.columnconfigure(col, weight=1)
            col += 1

            prev_btn:tk.Label = tk.Label(frame, image=self.bgstally.ui.image_icon_left_arrow, cursor="hand2")
            prev_btn.bind("<Button-1>", partial(self.event, "prev"))
            prev_btn.grid(row=row, column=col, sticky=tk.W)
            col += 1

            view_btn:tk.Label = tk.Label(frame, image=self.bgstally.ui.image_icon_change_view, cursor="hand2")
            view_btn.bind("<Button-1>", partial(self.event, "change"))
            view_btn.grid(row=row, column=col, sticky=tk.E)
            col += 1

            next_btn:tk.Label = tk.Label(frame, image=self.bgstally.ui.image_icon_right_arrow, cursor="hand2")
            next_btn.bind("<Button-1>", partial(self.event, "next"))
            next_btn.grid(row=row, column=col, sticky=tk.E)

            row += 1; col = 0

            # Progress bar chart
            #y=tk.LabelFrame(frame, border=0, height=10)
            #y.grid(row=row, column=col, columnspan=5, pady=0, sticky=tk.EW)
            #y.grid_rowconfigure(0, weight=1)
            #y.grid_propagate(0)
            #self.progvar = tk.IntVar()
            #style = ttk.Style()
            #style.configure("blue.Horizontal.TProgressbar", background='blue', lightcolor='blue', darkcolor='blue')
            #self.progbar = ttk.Progressbar(y, orient=tk.HORIZONTAL, variable=self.progvar, maximum=100, length=450, mode='determinate', style='blue.Horizontal.TProgressbar')
            #self.progbar.grid(row=0, column=0, columnspan=20, pady=0, ipady=0, sticky=tk.EW)
            #self.progbar.rowconfigure(0, weight=1)
            #row += 1; col = 0

            table_frame:tk.Frame = tk.Frame(frame)
            table_frame.columnconfigure(0, weight=1)
            table_frame.grid(row=row, column=col, columnspan=5, sticky=tk.NSEW)

            # Column headings
            row = 0
            for i, (k, v) in enumerate(self.headings.items()):
                if k == 'Carrier' and not self.bgstally.fleet_carrier.available():
                    continue

                c = tk.Label(table_frame, text=_(v.get(Units.TONNES)))#, cursor='hand2')
                c.grid(row=row, column=i, sticky=v.get('Sticky'))
                c.bind("<Button-1>", partial(self.change_view, k))

                self.weight(c)
                self.colheadings[k] = c

            row += 1

            for i, col in enumerate(self.headings.keys()):
                # Progress bar chart
                if col == 'Commodity':
                    continue
                fr:tk.LabelFrame = tk.LabelFrame(table_frame, border=1, height=10, width=70)
                fr.grid(row=row, column=i, pady=0, sticky=tk.EW)
                fr.grid_propagate(0)

                self.progcols[col] = tk.IntVar()
                pbar:ttk.Progressbar = ttk.Progressbar(fr, orient=tk.HORIZONTAL, variable=self.progcols[col], maximum=100, length=70, mode='determinate', style='blue.Horizontal.TProgressbar')
                pbar.grid(row=0, column=i, pady=0, ipady=0, sticky=tk.NSEW)

            row += 1

            # Go through the complete list of possible commodities and make a row for each and hide it.
            for c in self.colonisation.get_commodity_list('All'):
                r:dict = {}

                for i, (col, val) in enumerate(self.headings.items()):
                    lbl:tk.Label = tk.Label(table_frame, text='')
                    lbl.grid(row=row, column=i, sticky=val.get('Sticky'))
                    if col == 'Commodity':
                        lbl.bind("<Button-1>", partial(self.link, c))
                        #lbl.config(cursor='hand2')

                    r[col] = lbl
                self.rows.append(r)
                row += 1

            # Totals at the bottom
            r:dict = {}
            for i, (col, val) in enumerate(self.headings.items()):
                r[col] = tk.Label(table_frame, text=_("Total")) # LANG: Total amounts
                r[col].grid(row=row, column=i, sticky=val.get('Sticky'))
                self.weight(r[col])
            self.rows.append(r)
            self.table_frame = table_frame

            if len(tracked) == 0:
                Debug.logger.info("No tracked builds")
                frame.grid_forget()
                return

            if len(self.colonisation.get_required(tracked)) == 0:
                Debug.logger.info("No commodities to track")
                frame.grid_forget()
                return

            self.update_display()

        except Exception as e:
            Debug.logger.info(f"Error creating frame {e}")
            Debug.logger.error(traceback.format_exc())


    def event(self, event:str, tkEvent) -> None:
        '''
        Process events from the buttons in the progress window.
        '''
        try:
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
                    self.view = View((self.view.value + 1) % len(View))

            self.update_display()

        except Exception as e:
            Debug.logger.info(f"Error processing event {e}")
            Debug.logger.error(traceback.format_exc())


    def change_view(self, column:str, tkEvent) -> None:
        '''
        Change the view of the column when clicked. This is a toggle between tonnes, remaining, and loads.
        '''
        try:
            match column:
                case 'Commodity':
                    self.comm_order = CommodityOrder((self.comm_order.value + 1) % len(CommodityOrder))
                case _:
                    # Units -1 because PERCENT is disabled.
                    self.units[column] = Units((self.units[column].value + 1) % (len(Units)-1))

            self.update_display()

        except Exception as e:
            Debug.logger.info(f"Error processing link {e}")
            Debug.logger.error(traceback.format_exc())


    def link(self, comm:str, tkEvent) -> None:
        '''
        Open the link to Inara for nearest location for the commodity.
        '''
        try:
            comm_id = self.colonisation.base_costs['All'].get(comm)
            sys:str = self.colonisation.current_system if self.colonisation.current_system != None else 'sol'
            # pi3=3 - large, pi3=2 - medium
            size:int = 2 if self.colonisation.cargo_capacity < 407 else 3

            # pi7=5000 - supply (100, 500, 1000, 2500, 5000, 10000, 50000)
            tracked:dict = self.colonisation.get_tracked_builds()
            required:dict = self.colonisation.get_required(tracked)
            delivered:dict = self.colonisation.get_delivered(tracked)
            rem:int = (required[self.build_index].get(comm, 0) if len(required) > self.build_index else 0) - (delivered[self.build_index].get(comm, 0) if len(delivered) > self.build_index else 0)
            for min in [500, 1000, 2500, 5000, 10000, 50000]:
                if rem < min: break

            url:str = f"https://inara.cz/elite/commodities/?formbrief=1&pi1=1&pa1[]={comm_id}&ps1={sys}&pi10=3&pi11=0&pi3={size}&pi9=0&pi4=0&pi14=0&pi5=720&pi12=0&pi7={min}&pi8=0&pi13=0"
            webbrowser.open(url)

        except Exception as e:
            Debug.logger.info(f"Error processing link {e}")
            Debug.logger.error(traceback.format_exc())


    def update_display(self):
        '''
        Main display update function.
        '''
        try:
            tracked:list = self.colonisation.get_tracked_builds()
            required:dict = self.colonisation.get_required(tracked)
            delivered:dict = self.colonisation.get_delivered(tracked)

            if len(tracked) == 0 or self.colonisation.cargo_capacity < 8:
                self.frame.grid_forget()
                Debug.logger.debug("No progress to display")
                return

            self.frame.grid(row=self.frame_row, column=0, columnspan=20, sticky=tk.EW)
            self.table_frame.grid(row=2, column=0, columnspan=5, sticky=tk.NSEW)

            # Set the title
            name = _('All') # LANG: all builds
            if self.build_index < len(tracked):
                b:dict = tracked[self.build_index]
                bn = b.get('Name', '') if b.get('Name','') != '' else b.get('Base Type', '')
                pn = b.get('Plan', _('Unknown')) # Unknown system name
                name:str = ', '.join([pn, bn])

            self.title.config(text=name[-50:])

            # Set the column headings according to the selected units
            totals:dict = {}
            for col in self.headings.keys():
                if col == 'Carrier' and not self.bgstally.fleet_carrier.available():
                    continue
                self.colheadings[col]['text'] = self.headings[col][self.units[col]]
                totals[col] = 0

            totals['Delivered'] = 0
            totals['Commodity'] = _("Total")  # LANG: total

            # Go through each commodity and show or hide it as appropriate and display the appropriate values
            comms:list = self.colonisation.get_commodity_list('All', self.comm_order)
            if comms == None or comms == []:
                Debug.logger.info(f"No commodities found")
                return

            for i, c in enumerate(comms):
                row:dict = self.rows[i]
                reqcnt:int = required[self.build_index].get(c, 0) if len(required) > self.build_index else 0
                delcnt:int = delivered[self.build_index].get(c, 0) if len(delivered) > self.build_index else 0
                remaining:int = reqcnt - delcnt
                cargo:int = self.colonisation.cargo.get(c, 0)
                carrier:int = self.colonisation.carrier_cargo.get(c, 0)

                if reqcnt > 0:
                    totals['Required'] += reqcnt
                    totals['Delivered'] += delcnt
                if remaining > 0:
                    totals['Cargo'] += cargo
                    totals['Carrier'] += carrier

                # We only show required items. But.
                # If the view is reduced we don't show ones that are complete. Also,
                # If we're docked at a station, and in reduced view, we only show locally available commodities
                if reqcnt > 0 and \
                   (self.view == View.FULL or remaining > 0):
                   #(self.view == View.FULL or self.colonisation.docked == False or self.colonisation.market == {} or c in self.colonisation.market):

                    # Shorten and display the commodity name
                    colstr:str = self.colonisation.commodities[c].get('Name', c)
                    if len(colstr) > 25: colstr = colstr[0:23] + '…'
                    row['Commodity']['text'] = colstr
                    row['Commodity'].grid()

                    # Required
                    match self.units['Required']:
                        case Units.REMAINING:
                            reqstr = f"{remaining:,} {_('t')}" # LANG: Letter to indicate tonnes
                        case Units.LOADS:
                            reqstr = f"{ceil(remaining / self.colonisation.cargo_capacity)} {_('L')}" # LANG: Letter to indicate cargo loads
                        case Units.PERCENT:
                            reqstr = f"{delcnt * 100 / reqcnt:.0f}%"
                        case _:
                            reqstr = f"{reqcnt:,} t"

                    row['Required']['text'] = reqstr
                    row['Required'].grid()

                    # Delivered
                    match self.units['Delivered']:
                        case Units.REMAINING:
                            remstr = f"{max(remaining-cargo-carrier, 0):,} {_('t')}"
                        case Units.LOADS: # Trips
                            remstr = f"{ceil(delcnt / self.colonisation.cargo_capacity)} {_('L')}"
                        case Units.PERCENT: # Percentage
                            remstr = f"{delcnt * 100 / reqcnt:.0f}%"
                        case _: # Tonnes
                            remstr = f"{delcnt:,} {_('t')}"

                    row['Delivered']['text'] = remstr
                    row['Delivered'].grid()

                    # Cargo
                    match self.units['Cargo']:
                        case Units.REMAINING:
                            cargostr = f"{max(remaining-cargo, 0):,} {_('t')}"
                        case Units.LOADS: # Trips
                            cargostr = f"{ceil(cargo / self.colonisation.cargo_capacity)} {_('L')}"
                        case Units.PERCENT: # Percentage
                            cargostr = f"{cargo * 100 / reqcnt:.0f}%"
                        case _: # Tonnes
                            cargostr = f"{cargo:,} {_('t')}"

                    row['Cargo']['text'] = cargostr
                    row['Cargo'].grid()

                    # Carrier
                    match self.units['Carrier']:
                        case Units.REMAINING:
                            carrierstr = f"{max(remaining-carrier, 0):,} {_('t')}"
                        case Units.LOADS: # Trips
                            carrierstr = f"{ceil(carrier / self.colonisation.cargo_capacity)} {_('L')}"
                        case Units.PERCENT: # Percentage
                            carrierstr = f"{carrier * 100 / reqcnt:.0f}%"
                        case _: # Tonnes
                            carrierstr = f"{carrier:,} {_('t')}"

                    row['Carrier']['text'] = carrierstr
                    if self.bgstally.fleet_carrier.available():
                        row['Carrier'].grid()

                    self.highlight_row(row, c, remaining)

                else:
                    for col in self.headings.keys():
                        row[col].grid_remove()

            # Set the totals for each column depending on the selected unit view
            row:dict = self.rows[i+1]

            reqcnt:int = totals['Required']; delcnt = totals['Delivered']; remaining:int = reqcnt - delcnt; cargo:int = totals['Cargo']; carrier:int = totals['Carrier']
            for col in self.headings.keys():
                valstr:str = "Total"
                match self.units[col]:
                    case Units.REMAINING:
                        if col == 'Required': valstr = f"{remaining:,} {_('t')}"
                        if col == 'Delivered': valstr = f"{max(remaining-cargo-carrier, 0):,} {_('t')}"
                        if col == 'Cargo': valstr = f"{max(remaining-cargo, 0):,} {_('t')}"
                        if col == 'Carrier': valstr = f"{max(remaining-carrier,0):,} {_('t')}"
                    case Units.LOADS: # Trips
                        if col == 'Required': valstr = f"{ceil(remaining / self.colonisation.cargo_capacity)} {_('L')}"
                        if col == 'Delivered': valstr = f"{ceil(delcnt / self.colonisation.cargo_capacity)} {_('L')}"
                        if col == 'Cargo': valstr = f"{ceil(cargo / self.colonisation.cargo_capacity)} {_('L')}"
                        if col == 'Carrier': valstr = f"{ceil(carrier / self.colonisation.cargo_capacity)} {_('L')}"
                    case Units.PERCENT: # Percentage
                        if col == 'Required': valstr = f"{delcnt * 100 / reqcnt:.0f}%"
                        if col == 'Delivered': valstr = f"{delcnt * 100 / reqcnt:.0f}%"
                        if col == 'Cargo': valstr = f"{cargo * 100 / cargo:.0f}%"
                        if col == 'Carrier': valstr = f"{carrier * 100 / reqcnt:.0f}%"
                    case _: # Tonnes
                        if col == 'Required': valstr = f"{reqcnt:,} {_('t')}"
                        if col == 'Delivered': valstr = f"{delcnt:,} {_('t')}"
                        if col == 'Cargo': valstr = f"{cargo:,} {_('t')}"
                        if col == 'Carrier': valstr = f"{carrier:,} {_('t')}"
                row[col]['text'] = valstr

            self.progcols['Required'].set(remaining * 100 / reqcnt)
            self.progcols['Delivered'].set(delcnt * 100 / reqcnt)
            self.progcols['Cargo'].set(cargo * 100 / self.colonisation.cargo_capacity)
            if remaining > 0:
                self.progcols['Carrier'].set(carrier * 100 / remaining) # Need to figure out carrier space

            if remaining == 0:
                if len(tracked) == 1:
                    self.frame.grid_forget()
                else:
                    self.table_frame.grid_forget()

                Debug.logger.debug(f"No progress to display {reqcnt} {delcnt} {remaining} {cargo} {carrier}")
                return

        except Exception as e:
            Debug.logger.info(f"Error updating display")
            Debug.logger.error(traceback.format_exc())


    def weight(self, item, w='bold') -> None:
        '''
        Set font weight, defaults to bold
        '''
        fnt:tkFont.Font = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], w))


    def highlight_row(self, row:dict, c:str, qty:int = 0) -> None:
        '''
        Highlight rows depending on the state
        '''
        tobuy:int = qty - self.colonisation.carrier_cargo.get(c, 0) - self.colonisation.cargo.get(c, 0)
        space:int = self.colonisation.cargo_capacity - sum(self.colonisation.cargo.values())

        for col in self.headings.keys():
            row[col]['fg'] = None; self.weight(row[col], 'normal') # Start black & normal

            if self.colonisation.carrier_cargo.get(c, 0) >= qty: # Have relevant carrier cargo
                row[col]['fg'] = 'darkgreen'; self.weight(row[col], 'normal')

            # Amount we have in our hold
            if self.colonisation.cargo.get(c, 0) >= qty:
                row[col]['fg'] = 'darkslategrey'; self.weight(row[col], 'normal')

            # What's available at this market if we need any and have room
            if tobuy > 0 and self.colonisation.docked == True and self.colonisation.market.get(c, 0): # market!
                row[col]['fg'] = 'steelblue'
                self.weight(row[col], 'bold' if qty > 0 and space > 0 else 'normal')

            # Nothing left to do
            if qty <= 0:
                row[col]['fg'] = 'grey'; self.weight(row[col], 'normal')
