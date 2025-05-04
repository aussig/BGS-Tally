import traceback
import tkinter as tk
import tkinter.font as tkFont
from math import ceil
from tkinter import ttk
from typing import Dict, List, Optional
from enum import Enum
from functools import partial
import webbrowser

from bgstally.debug import Debug
from bgstally.utils import _

class View(Enum):
    FULL = 0
    REDUCED = 1

class Units(Enum):
    TONNES = 0
    REMAINING = 1
    LOADS = 2
    PERCENT = 3

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

        self.progbar = None
        #self.progvar = None
        self.progcols = {}
        self.columns = {'Commodity': tk.W, 'Required': tk.E, 'Delivered':tk.E, 'Cargo':tk.E, 'Carrier': tk.E}
        self.units = {'Commodity': Units.TONNES, 'Required': Units.TONNES, 'Delivered':Units.TONNES, 'Cargo':Units.TONNES, 'Carrier': Units.TONNES}
        self.headings = {'Commodity': {Units.TONNES: f"{_('Commodity'):>11}", Units.REMAINING: f"{_('Commodity'):>11}", Units.PERCENT: f"{_('Commodity'):>11}", Units.LOADS: f"{_('Commodity'):>11}"},
                         'Required': {Units.TONNES: f"{_('Required'):>10}", Units.REMAINING: f"{_('Needed'):>10}", Units.PERCENT: f"{_('Percent'):>11}", Units.LOADS: f"{_('Trips'):>11}"},
                         'Delivered': {Units.TONNES: f"{_('Delivered'):>10}", Units.REMAINING: f"{_('To Buy'):>11}", Units.PERCENT: f"{_('Percent'):>11}", Units.LOADS: f"{_('Trips'):>11}"},
                         'Cargo': {Units.TONNES: f"{_('Cargo'):>1}", Units.REMAINING: f"{_('Needed'):>9}", Units.PERCENT: f"{_('Percent'):>11}", Units.LOADS: f"{_('Trips'):>11}"},
                         'Carrier': {Units.TONNES: f"{_('Carrier'):>11}", Units.REMAINING: f"{_('Needed'):>9}", Units.PERCENT: f"{_('Percent'):>11}", Units.LOADS: f"{_('Trips'):>11}"}
                        }

        # our tracking data
        self.tracked = []
        self.required = []
        self.delivered = []

        # UI components
        self.frame_row = 5
        self.colheadings = {}
        self.rows = []
        self.build_index = 0
        self.view = View.REDUCED

        self.show_percentage = True  # Toggle between percentage and ship loads
        self.minimal = False #


    def create_frame(self, parent_frame:tk.Frame, row:int, column_count:int) -> None:
        """
        Create the progress frame
        """
        try:
            Debug.logger.debug("Creating progress frame")
            self.colonisation = self.bgstally.colonisation
            self.tracked = self.colonisation.get_tracked_builds()
            Debug.logger.debug(f"Tracking builds: {self.tracked}")

            self.frame = tk.Frame(parent_frame)
            self.frame.grid(row=row, column=0, columnspan=20, sticky=tk.EW)
            self.frame_row = row

            row = 0; col = 0

            ttk.Separator(self.frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=5, pady=2, sticky=tk.EW)
            row += 1

            lbl = tk.Label(self.frame, text=_("Builds") + ":", anchor=tk.W)
            lbl.grid(row=row, column=0, sticky=tk.W)
            self.weight(lbl)
            col += 1

            self.title = tk.Label(self.frame, text="None", justify=tk.CENTER, anchor=tk.CENTER)
            self.title.grid(row=row, column=col, sticky=tk.EW)
            self.frame.columnconfigure(col, weight=1)
            col += 1

            self.prev_btn = tk.Label(self.frame, image=self.bgstally.ui.image_icon_left_arrow, cursor="hand2")
            self.prev_btn.bind("<Button-1>", partial(self.event, "prev"))
            self.prev_btn.grid(row=row, column=col, sticky=tk.W)
            col += 1

            self.view_btn = tk.Label(self.frame, image=self.bgstally.ui.image_icon_change_view, cursor="hand2")
            self.view_btn.bind("<Button-1>", partial(self.event, "change"))
            self.view_btn.grid(row=row, column=col, sticky=tk.E)
            col += 1

            self.next_btn = tk.Label(self.frame, image=self.bgstally.ui.image_icon_right_arrow, cursor="hand2")
            self.next_btn.bind("<Button-1>", partial(self.event, "next"))
            self.next_btn.grid(row=row, column=col, sticky=tk.E)

            row += 1; col = 0

            # Progress bar chart
            #y=tk.LabelFrame(self.frame, border=0, height=10)
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

            self.table_frame = tk.Frame(self.frame)
            self.table_frame.columnconfigure(0, weight=1)
            self.table_frame.grid(row=row, column=col, columnspan=5, sticky=tk.NSEW)

            # Column headings
            row = 0
            for i, col in enumerate(self.columns.keys()):
                c = tk.Label(self.table_frame, text=_(col), cursor='hand2', fg='black')
                c.grid(row=row, column=i, sticky=self.columns[col])
                c.bind("<Button-1>", partial(self.change_view, col))
                self.weight(c)
                self.colheadings[col] = c
            row += 1

            for i, col in enumerate(self.columns.keys()):
                # Progress bar chart
                if col == 'Commodity':
                    continue
                fr=tk.LabelFrame(self.table_frame, border=1, height=10, width=70)
                fr.grid(row=row, column=i, pady=0, sticky=tk.EW)
                fr.grid_propagate(0)

                self.progcols[col] = tk.IntVar()
                pbar = ttk.Progressbar(fr, orient=tk.HORIZONTAL, variable=self.progcols[col], maximum=100, length=70, mode='determinate', style='Horizontal.TProgressbar')
                pbar.grid(row=0, column=i, pady=0, ipady=0, sticky=tk.NSEW)

            row += 1

            # Go through the complete list of possible commodities and make a row for each and hide it.
            for c in self.colonisation.base_costs['All'].keys():
                r = {}

                for i, col in enumerate(self.columns.keys()):
                    lbl = tk.Label(self.table_frame, text='')
                    if col == 'Commodity':
                        lbl.bind("<Button-1>", partial(self.link, c))
                        lbl.config(cursor='hand2')

                    lbl.grid(row=row, column=i, sticky=self.columns[col])
                    r[col] = lbl
                self.rows.append(r)
                row += 1

            # Totals at the bottom
            r = {}
            for i, (col, val) in enumerate(self.columns.items()):
                r[col] = tk.Label(self.table_frame, text=_("Total"))
                r[col].grid(row=row, column=i, sticky=val)
                self.weight(r[col])
            self.rows.append(r)

            if len(self.tracked) == 0:
                Debug.logger.info("No tracked builds")
                self.frame.grid_forget()
                return

            self.required = self.colonisation.get_required(self.tracked)
            if len(self.required) == 0:
                Debug.logger.info("No commodities to track")
                self.frame.grid_forget()
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
            max = len(self.tracked) -1 if len(self.tracked) < 2 else len(self.tracked) # "All" if more than one build
            match event:
                case 'next':
                    self.build_index += 1
                    if self.build_index > max: self.build_index = 0

                case 'prev':
                    self.build_index -= 1
                    if self.build_index < 0: self.build_index = max

                case 'change':
                    if (self.view == View.FULL):
                        self.view = View.REDUCED
                    elif (self.view == View.REDUCED):
                        self.view = View.FULL

            self.update_display()

        except Exception as e:
            Debug.logger.info(f"Error processing event {e}")
            Debug.logger.error(traceback.format_exc())


    def change_view(self, column:str, tkEvent) -> None:
        '''
        Change the view of the column when clicked. This is a toggle between tonnes, remaining, and loads.
        '''
        try:
            match self.units[column]:
                case Units.TONNES:
                    self.units[column] = Units.REMAINING
                case Units.REMAINING:
                    self.units[column] = Units.LOADS
                case Units.LOADS:
                    # PERCENT is disabled since we have the progress bars instead
                    #self.units[column] = Units.PERCENT
                    self.units[column] = Units.TONNES
                case _:
                    self.units[column] = Units.TONNES
            self.update_display()

        except Exception as e:
            Debug.logger.info(f"Error processing link {e}")
            Debug.logger.error(traceback.format_exc())


    def link(self, comm:str, tkEvent) -> None:
        '''
        Open the link to Inara for nearest location for the commodity.
        '''
        try:
            Debug.logger.debug(f"Link called")
            comm_id = self.colonisation.base_costs['All'].get(comm)
            sys = self.bgstally.state.current_system if self.bgstally.state.current_system != None else 'sol'
            # pi3=3 - large, pi3=2 - medium
            size = 2 if self.colonisation.cargo_capacity < 407 else 3

            # pi7=5000 - supply (100, 500, 1000, 2500, 5000, 10000, 50000)
            rem = (self.required[self.build_index].get(comm, 0) if len(self.required) > self.build_index else 0) - (self.delivered[self.build_index].get(comm, 0) if len(self.delivered) > self.build_index else 0)
            for min in [500, 1000, 2500, 5000, 10000, 50000]:
                if rem < min: break

            qty = self.colonisation.base_costs
            url = f"https://inara.cz/elite/commodities/?formbrief=1&pi1=1&pa1[]={comm_id}&ps1={sys}&pi10=3&pi11=0&pi3={size}&pi9=0&pi4=0&pi14=0&pi5=720&pi12=0&pi7={min}&pi8=0&pi13=0"
            Debug.logger.debug(f"Opening URL {url}")
            webbrowser.open(url)

        except Exception as e:
            Debug.logger.info(f"Error processing link {e}")
            Debug.logger.error(traceback.format_exc())


    def update_display(self):
        '''
        Main display update function.
        '''
        try:
            self.tracked = self.colonisation.get_tracked_builds()
            self.required = self.colonisation.get_required(self.tracked)
            self.delivered = self.colonisation.get_delivered(self.tracked)

            if len(self.tracked) == 0:
                Debug.logger.debug("No progress to display")
                return

            # Set the title
            name = ', '.join([self.tracked[self.build_index].get('Plan', 'Unknown'), self.tracked[self.build_index].get('Name', 'Unnamed')]) if self.build_index < len(self.tracked) else _('All')
            self.title.config(text=name)

            # Set the column headings accordin to the selected units
            totals = {}
            for col in self.columns.keys():
                self.colheadings[col]['text'] = self.headings[col][self.units[col]]
                totals[col] = 0

            totals['Delivered'] = 0
            totals['Commodity'] = _("Total")

            # Go through eacy commodity and show or hide it as appropriate and display the appropriate values
            for i, c in enumerate(self.colonisation.base_costs['All'].keys()):                
                row = self.rows[i]
                required = self.required[self.build_index].get(c, 0) if len(self.required) > self.build_index else 0
                delivered = self.delivered[self.build_index].get(c, 0) if len(self.delivered) > self.build_index else 0
                remaining = required - delivered
                cargo = self.colonisation.cargo.get(c, 0)
                carrier = self.colonisation.carrier_cargo.get(c, 0)

                if required > 0:
                    totals['Required'] += required
                    totals['Delivered'] += delivered
                    totals['Cargo'] += cargo
                    totals['Carrier'] += carrier

                # We only show required items. But.
                # If the view is reduced we don't show ones that are complete. Also,
                # If we're docked at a station, and in reduced view, we only show locally available commodities
                if required > 0 and \
                   (self.view == View.FULL or remaining > 0) and \
                   (self.view == View.FULL or self.colonisation.docked == False or self.colonisation.market == {} or c in self.colonisation.market):
                    
                    # Shorten and display the commodity name
                    colstr = self.colonisation.commodities.get(c, c)
                    if len(colstr) > 25: colstr = colstr[0:23] + '…'
                    row['Commodity']['text'] = colstr
                    row['Commodity'].grid()

                    # Required
                    match self.units['Required']:
                        case Units.REMAINING:
                            reqstr = f"{remaining:,}"
                        case Units.LOADS:
                            reqstr = f"{ceil(required / self.colonisation.cargo_capacity)} L"
                        case Units.PERCENT:
                            reqstr = f"{delivered * 100 / required:.0f}%"
                        case _:
                            reqstr = f"{required:,}"

                    row['Required']['text'] = reqstr
                    row['Required'].grid()

                    # Delivered
                    match self.units['Delivered']:
                        case Units.REMAINING:
                            remstr = f"{max(remaining-cargo-carrier, 0):,}"
                        case Units.LOADS: # Trips
                            remstr = f"{ceil(delivered / self.colonisation.cargo_capacity)} L"
                        case Units.PERCENT: # Percentage
                            remstr = f"{delivered * 100 / required:.0f}%"
                        case _: # Tonnes
                            remstr = f"{delivered:,}"

                    row['Delivered']['text'] = remstr
                    row['Delivered'].grid()

                    # Cargo
                    match self.units['Cargo']:
                        case Units.REMAINING:
                            cargostr = f"{max(remaining-cargo, 0):,}"
                        case Units.LOADS: # Trips
                            cargostr = f"{ceil(cargo / self.colonisation.cargo_capacity)} L"
                        case Units.PERCENT: # Percentage
                            cargostr = f"{cargo * 100 / required:.0f}%"
                        case _: # Tonnes
                            cargostr = f"{cargo:,}"

                    row['Cargo']['text'] = cargostr
                    row['Cargo'].grid()

                    # Carrier
                    match self.units['Carrier']:
                        case Units.REMAINING:
                            carrierstr = f"{max(remaining-carrier, 0):,}"
                        case Units.LOADS: # Trips
                            carrierstr = f"{ceil(carrier / self.colonisation.cargo_capacity)} L"
                        case Units.PERCENT: # Percentage
                            carrierstr = f"{carrier * 100 / required:.0f}%"
                        case _: # Tonnes
                            carrierstr = f"{carrier:,}"

                    row['Carrier']['text'] = carrierstr
                    row['Carrier'].grid()

                    self.highlight_row(row, c, remaining)

                else:
                    for col in self.columns.keys():
                        row[col].grid_remove()

            # Set the totals for each column depending on the selected unit view
            row = self.rows[i+1]

            required = totals['Required']; delivered = totals['Delivered']; remaining = required-delivered; cargo = totals['Cargo']; carrier = totals['Carrier']
            for col in self.columns.keys():
                valstr = "Total"
                match self.units[col]:
                    case Units.REMAINING:
                        if col == 'Required': valstr = f"{remaining:,}"
                        if col == 'Delivered': valstr = f"{max(remaining-cargo-carrier, 0):,}"
                        if col == 'Cargo': valstr = f"{max(remaining-cargo, 0):,}"
                        if col == 'Carrier': valstr = f"{max(remaining-carrier,0):,}"
                    case Units.LOADS: # Trips
                        if col == 'Required': valstr = f"{ceil(required / self.colonisation.cargo_capacity)} L"
                        if col == 'Delivered': valstr = f"{ceil(delivered / self.colonisation.cargo_capacity)} L"
                        if col == 'Cargo': valstr = f"{ceil(cargo / self.colonisation.cargo_capacity)} L"
                        if col == 'Carrier': valstr = f"{ceil(carrier / self.colonisation.cargo_capacity)} L"
                    case Units.PERCENT: # Percentage
                        if col == 'Required': valstr = f"{delivered * 100 / required:.0f}%"
                        if col == 'Delivered': valstr = f"{delivered * 100 / required:.0f}%"
                        if col == 'Cargo': valstr = f"{cargo * 100 / cargo:.0f}%"
                        if col == 'Carrier': valstr = f"{carrier * 100 / required:.0f}%"
                    case _: # Tonnes
                        if col == 'Required': valstr = f"{required:,}"
                        if col == 'Delivered': valstr = f"{delivered:,}"
                        if col == 'Cargo': valstr = f"{cargo:,}"
                        if col == 'Carrier': valstr = f"{carrier:,}"
                row[col]['text'] = valstr

            self.progcols['Required'].set(remaining * 100 / required)
            self.progcols['Delivered'].set(delivered * 100 / required)
            self.progcols['Cargo'].set(cargo * 100 / self.colonisation.cargo_capacity)
            self.progcols['Carrier'].set(carrier * 100 / remaining) # Need to figure out carrier space

        except Exception as e:
            Debug.logger.info(f"Error updating display")
            Debug.logger.error(traceback.format_exc())


    def weight(self, item, w='bold') -> None:
        '''
        Set font weight, defaults to bold
        '''
        fnt = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], w))

    def highlight_row(self, row, c, qty = 0) -> None:
        '''
        Highlight rows depending on the state of the row.
        '''
        tobuy = qty - self.colonisation.carrier_cargo.get(c, 0) - self.colonisation.cargo.get(c, 0)
        space = self.colonisation.cargo_capacity - self.colonisation.cargo.get(c, 0)

        for col in self.columns.keys():
            row[col]['fg'] = 'black'; self.weight(row[col], 'normal') # Start black & normal

            if self.colonisation.carrier_cargo.get(c, 0) >= qty: # Have relevant carrier cargo
                row[col]['fg'] = 'darkgreen'; self.weight(row[col], 'normal')

            # Amount we have in our hold
            if self.colonisation.cargo.get(c, 0) >= qty:
                row[col]['fg'] = 'darkslategrey'; self.weight(row[col], 'normal')

            # What's available at this market if we need any and have room
            if self.colonisation.docked == True and c in self.colonisation.market: # market!
                row[col]['fg'] = 'steelblue'
                self.weight(row[col], 'bold' if qty > 0 and space > 0 else 'normal')

            # Nothing left to buy
            if tobuy <= 0:
                row[col]['fg'] = 'grey'; self.weight(row[col], 'normal')
