import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional
from enum import Enum
from functools import partial

from bgstally.constants import FONT_TEXT_BOLD
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

        self.columns = {'Commodity': tk.W, 'Required': tk.E, 'Delivered':tk.E, 'Cargo':tk.E, 'Carrier': tk.E}

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

        self.frame = tk.Frame(parent_frame)
        self.frame.grid(row=row, column=0, columnspan=20, sticky=tk.EW)
        self.frame_row = row
        row = 0

        tk.Label(self.frame, text="Builds:", anchor=tk.W).grid(row=row, column=0, sticky=tk.W)
        self.frame.columnconfigure(1, weight=1)
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

        row = 0
        for i, col in enumerate(self.columns.keys()):
            c = tk.Label(self.table_frame, text=col)
            c.grid(row=row, column=i, sticky=self.columns[col])

        self.carrier_col = c
        row += 1

        ttk.Separator(self.table_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=5, pady=2, sticky=tk.EW)
        row += 1

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
        Debug.logger.debug(f"Processing event {event}")

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

        if self.build_index != curr:
            self.update_display()

    def update_display(self):
        Debug.logger.debug(f"Updating table")

        self.tracked = self.colonisation.get_tracked_builds()
        self.required = self.colonisation.get_required(self.tracked)
        self.delivered = self.colonisation.get_delivered(self.tracked)

        if len(self.tracked) == 0:
            Debug.logger.debug("No progress to display")
            #if self.frame != None:
            #    Debug.logger.debug(f"Hiding frame")
            #    self.frame.grid_forget()
            return

        Debug.logger.debug(f"Updating display for {self.build_index} of {len(self.tracked)} builds")
        # Show frame.
        #self.frame.grid(row=self.frame_row, column=0, columnspan=20, sticky=tk.EW)

        name = ', '.join([self.tracked[self.build_index].get('Plan', 'Unknown'), self.tracked[self.build_index].get('Name', 'Unnamed')]) if self.build_index < len(self.tracked) else _('All')
        self.title.config(text=name)

        totals = {}
        for col in self.columns.keys():
            totals[col] = 0
        totals['Commodity'] = 'Total'

        for i, c in enumerate(self.colonisation.base_costs['All'].keys()):
            # If any of them are required display a row.
            row = self.rows[i]
            req = self.required[self.build_index].get(c, 0) if len(self.required) > self.build_index else 0
            if req > 0:
                row['Commodity']['text'] = c
                row['Commodity'].grid()

                v = self.required[self.build_index].get(c, 0) if len(self.required) > self.build_index else 0
                totals['Required'] += v
                row['Required']['text'] = f"{v:,}"
                row['Required'].grid()

                v = self.delivered[self.build_index].get(c, 0) if len(self.delivered) >= self.build_index else 0
                totals['Delivered'] += v
                row['Delivered']['text'] = f"{v:,}"
                row['Delivered'].grid()

                v = self.colonisation.cargo.get(c, 0)
                totals['Cargo'] += v
                row['Cargo']['text'] = f"{v:,}"
                row['Cargo'].grid()

                v = self.colonisation.carrier_cargo.get(c, 0)
                totals['Carrier'] += v
                row['Carrier']['text'] = f"{v:,}"
                row['Carrier'].grid()

                self.colorRow(row, c, req)

            else:
                for col in self.columns.keys():
                    row[col].grid_remove()

        row = self.rows[i+1]
        for c in totals.keys():
            if c == 'Commodity':
                row[c]['text'] = totals[c]
            else:
                row[c]['text'] = f"{totals[c]:,}"
            row[c].grid()

    def colorRow(self, row, c, qty):
        #Debug.logger.debug(f"Coloring row for {commodity}")

        for col in self.columns.keys():
            row[col]['fg'] = 'black'
            if c in self.colonisation.market: # market!
                row[col]['fg'] = 'cyan'
            if self.colonisation.carrier_cargo.get(c, 0) > qty:
                row[col]['fg'] = 'darkgreen'
            if self.required[self.build_index].get(c, 0) == 0:
                row[col]['fg'] = 'green'
