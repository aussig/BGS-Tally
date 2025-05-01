import traceback
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk
from typing import Dict, List, Optional
from enum import Enum
from functools import partial

from bgstally.debug import Debug
from bgstally.utils import _

class View(Enum):
    FULL = 0
    FILTERED = 1

MAX_ROWS = 35

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

        self.columns = {'Commodity': tk.W, 'Required': tk.E, 'Remaining':tk.E, 'Cargo':tk.E, 'Carrier': tk.E}

#       # our tracking data
        self.tracked = []
        self.required = []
        self.delivered = []

        # UI components
        self.parent_frame = None
        self.frame_row = 5
        self.rows = []
        self.build_index = 0
        self.show_percentage = True  # Toggle between percentage and ship loads
        self.minimal = False #
        self.carrier_col = False

    def create_frame(self, parent_frame, row, column_count):
        """
        Create the progress frame
        """
        Debug.logger.debug("Creating progress frame")
        self.colonisation = self.bgstally.colonisation
        self.tracked = self.colonisation.get_tracked_builds()
        Debug.logger.debug(f"Tracking builds: {self.tracked}")

        self.frame = tk.Frame(parent_frame)
        self.frame.grid(row=row, column=0, columnspan=20, sticky=tk.EW)
        self.frame_row = row
        row = 0

        lbl = tk.Label(self.frame, text="Builds:", anchor=tk.W)
        lbl.grid(row=row, column=0, sticky=tk.W)
        self.frame.columnconfigure(1, weight=1)
        self.weight(lbl)
        self.prev_btn = tk.Label(self.frame, image=self.bgstally.ui.image_icon_left_arrow, cursor="hand2")
        self.prev_btn.bind("<Button-1>", partial(self.event, "prev"))
        self.prev_btn.grid(row=row, column=2, sticky=tk.W)

        self.title = tk.Label(self.frame, text="None", justify=tk.CENTER, anchor=tk.CENTER)
        self.title.grid(row=row, column=1, sticky=tk.EW)

        self.next_btn = tk.Label(self.frame, image=self.bgstally.ui.image_icon_right_arrow, cursor="hand2")
        self.next_btn.bind("<Button-1>", partial(self.event, "next"))
        self.next_btn.grid(row=row, column=3, sticky=tk.E)
        row += 1
        #self.view_btn = tk.Label(self.frame, image=self.icons['view_close'], cursor="hand2")
        #self.view_btn.bind("<Button-1>", self.changeView)
        #self.view_btn.grid(row=0, column=4, sticky=tk.E)

        #self.table_frame = tk.Frame(self.frame, borderwidth=1, relief="solid")
        self.table_frame = tk.Frame(self.frame)
        self.table_frame.columnconfigure(0, weight=1)
        self.table_frame.grid(row=row, column=0, columnspan=4, sticky=tk.NSEW)

        # Column headings
        row = 0
        for i, col in enumerate(self.columns.keys()):
            c = tk.Label(self.table_frame, text=col)
            c.grid(row=row, column=i, sticky=self.columns[col])
            self.weight(c)

        self.carrier_col = c
        row += 1

        #ttk.Separator(self.table_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=5, pady=2, sticky=tk.EW)
        #row += 1

        # Go through the complete list of possible commodities and make a row for each and hide it.
        for c in self.colonisation.base_costs['All'].keys():
            # If any of them are required display a row.
            r = {}

            for i, col in enumerate(self.columns.keys()):
                r[col] = tk.Label(self.table_frame, text='')
                r[col].grid(row=row, column=i, sticky=self.columns[col])
            self.rows.append(r)
            row += 1

        # Totals at the bottom
        r = {}
        for i, col in enumerate(self.columns.keys()):
            r[col] = tk.Label(self.table_frame, text='Total')
            r[col].grid(row=row, column=i, sticky=self.columns[col])
            self.weight(r[col])
        self.rows.append(r)

        if len(self.tracked) == 0:
            Debug.logger.info('No tracked builds')
            self.frame.grid_forget()
            return

        self.required = self.colonisation.get_required(self.tracked)
        if len(self.required) == 0:
            Debug.logger.info('No commodities to track')
            self.frame.grid_forget()
            return

        self.update_display()

    def event(self, event, tkEvent):
        #Debug.logger.debug(f"Processing event {event}")

        curr = self.build_index
        max = len(self.tracked) -1 if len(self.tracked) < 2 else len(self.tracked) # "All" if more than one build
        match event:
            case 'next':
                self.build_index += 1
                if self.build_index > max:
                    self.build_index = 0

            case 'prev':
                self.build_index -= 1
                if self.build_index < 0:
                    self.build_index = max

            #case 'view':
            #    if (self.view_mode == View.FULL):
            #        self.view_btn['image'] = self.icons['view_open']
            #        self.view_mode = View.FILTERED
            #    elif (self.view_mode == View.FILTERED):
            #        self.view_btn['image'] = self.icons['view_close']
            #        self.view_mode = View.FULL

            case 'link':
                # Open the system in Inara
                sys = self.bgstally.state.current_system
                if not sys:
                    return

                url = f":https://inara.cz/elite/commodities/?formbrief=1&pi1=1&pa1={comm_id}&ps1={sys}&pi10=3&pi11=0&pi3=1&pi9=0&pi4=0&pi14=0&pi5=720&pi12=0&pi7=0&pi8=0&pi13=0"
                url = f"https://inara.cz/elite/search/?search={star}"
                webbrowser.open(url)

        if self.build_index != curr:
            self.update_display()

    def update_display(self):
        try:
            Debug.logger.debug(f"Updating progress display")

            self.tracked = self.colonisation.get_tracked_builds()
            self.required = self.colonisation.get_required(self.tracked)
            self.delivered = self.colonisation.get_delivered(self.tracked)

            #Debug.logger.debug(f"Carrier cargo: {self.colonisation.carrier_cargo}")
            #Debug.logger.debug(f"Cargo: {self.colonisation.cargo}")
            if len(self.tracked) == 0:
                Debug.logger.debug("No progress to display")
                return

            Debug.logger.debug(f"Updating display for {self.build_index} of {len(self.tracked)} builds")
            # Show frame.
            #self.frame.grid(row=self.frame_row, column=0, columnspan=20, sticky=tk.EW)

            if self.build_index >= len(self.tracked):
                self.build_index = 0

            Debug.logger.debug(f"{self.tracked}")
            name = ', '.join([self.tracked[self.build_index].get('Plan', 'Unknown'), self.tracked[self.build_index].get('Name', 'Unnamed')]) if self.build_index < len(self.tracked) else _('All')
            self.title.config(text=name)

            totals = {}
            for col in self.columns.keys():
                totals[col] = 0
            totals['Commodity'] = 'Total'

            for i, c in enumerate(self.colonisation.base_costs['All'].keys()):
                # If any of them are required display the cell and the amount.
                row = self.rows[i]
                req = self.required[self.build_index].get(c, 0) if len(self.required) > self.build_index else 0
                if req > 0:
                    row['Commodity']['text'] = self.colonisation.local_names.get(c, c)
                    row['Commodity'].grid()

                    v = self.required[self.build_index].get(c, 0) if len(self.required) > self.build_index else 0
                    totals['Required'] += v
                    row['Required']['text'] = f"{v:,}"
                    row['Required']['fg'] = 'lightgrey' if self.delivered[self.build_index].get(c, 0) > 0 else 'black'
                    row['Required'].grid()

                    v = self.required[self.build_index].get(c, 0)
                    if len(self.delivered) > self.build_index:
                        v -= self.delivered[self.build_index].get(c, 0)

                    totals['Remaining'] += v
                    row['Remaining']['text'] = f"{v:,}"
                    row['Remaining'].grid()

                    v = self.colonisation.cargo.get(c, 0)
                    totals['Cargo'] += v
                    row['Cargo']['text'] = f"{v:,}"
                    row['Cargo'].grid()

                    v = self.colonisation.carrier_cargo.get(c, 0)
                    totals['Carrier'] += v
                    row['Carrier']['text'] = f"{v:,}"
                    row['Carrier'].grid()

                    self.color_row(row, c, req)

                else:
                    for col in self.columns.keys():
                        row[col].grid_remove()

            row = self.rows[i+1]
            for c in totals.keys():
                if c == 'Commodity':
                    row[c]['text'] = totals[c]
                else:
                    row[c]['text'] = f"{totals[c]:,}"
                    self.weight(row[c])
                row[c].grid()
        except Exception as e:
            Debug.logger.info(f"Error updating display")
            Debug.logger.error(traceback.format_exc())


    def weight(self, item, w='bold'):
        fnt = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], w))

    def color_row(self, row, c, qty):
        #Debug.logger.debug(f"Coloring row for {c} {self.colonisation.carrier_cargo.get(c, 0)} {}")

        for col in self.columns.keys():
            row[col]['fg'] = 'black'
            self.weight(row[col], 'normal')
            if self.colonisation.carrier_cargo.get(c, 0) > 0:
                row[col]['fg'] = 'darkgreen'
                self.weight(row[col], 'normal')
            if c in self.colonisation.market: # market!
                row[col]['fg'] = 'steelblue'
                self.weight(row[col])
            if self.colonisation.cargo.get(c, 0) > 0:
                row[col]['fg'] = 'darkslategrey'
                self.weight(row[col])
            if self.required[self.build_index].get(c, 0) < self.colonisation.carrier_cargo.get(c, 0) + self.colonisation.cargo.get(c, 0):
                row[col]['fg'] = 'green'
                self.weight(row[col], 'normal')
