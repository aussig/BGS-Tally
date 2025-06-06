import traceback
import tkinter as tk
import tkinter.font as tkFont
from math import ceil
from tkinter import ttk
from enum import Enum, auto
from functools import partial
from thirdparty.Tooltip import ToolTip
import webbrowser
from urllib.parse import quote
from bgstally.constants import CommodityOrder, ProgressUnits, ProgressView
from config import config
from bgstally.debug import Debug
from bgstally.utils import _

MAX_ROWS = 20

#@TODO: replace f"{}:," with string_from_number()
class ProgressWindow:
    ''' Window for displaying construction progress for Elite Dangerous colonisation '''
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.colonisation = None

        self.units:dict = {'Commodity': ProgressUnits.TONNES, 'Required': ProgressUnits.TONNES,
                           'Delivered': ProgressUnits.TONNES, 'Cargo': ProgressUnits.TONNES,
                           'Carrier': ProgressUnits.TONNES}

        self.headings:dict = {
            'Commodity': {
                ProgressUnits.TONNES: f"{_('Commodity'):<11}", # LANG: Commodity
                ProgressUnits.REMAINING: f"{_('Commodity'):<11}",
                ProgressUnits.PERCENT: f"{_('Commodity'):<11}",
                ProgressUnits.LOADS: f"{_('Commodity'):<11}",
                'Sticky': tk.W
                },
            'Required': {
                ProgressUnits.TONNES: f"{_('Required'):>10}", # LANG: Required amount
                ProgressUnits.REMAINING: f"{_('Needed'):>10}", # LANG: Amount still needed
                ProgressUnits.PERCENT: f"{_('Percent'):>11}", # LANG: Percentage
                ProgressUnits.LOADS: f"{_('Loads'):>12}", # LANG: number of cargo loads
                'Sticky': tk.E
                },
            'Delivered': {
                ProgressUnits.TONNES: f"{_('Delivered'):>10}", # LANG: Amount delivered
                ProgressUnits.REMAINING: f"{_('To Buy'):>11}", # LANG: Amount still left to buy
                ProgressUnits.PERCENT: f"{_('Percent'):>11}",
                ProgressUnits.LOADS: f"{_('Loads'):>12}",
                'Sticky': tk.E
                },
            'Cargo': {
                ProgressUnits.TONNES: f"{_('Cargo'):>1}", # LANG: amount in ship's Cargo
                ProgressUnits.REMAINING: f"{_('Needed'):>9}",
                ProgressUnits.PERCENT: f"{_('Percent'):>11}",
                ProgressUnits.LOADS: f"{_('Loads'):>12}",
                'Sticky': tk.E
                },
            'Carrier': {
                ProgressUnits.TONNES: f"{_('Carrier'):>11}", # LANG: Amount in your Fleet Carrier
                ProgressUnits.REMAINING: f"{_('Needed'):>9}",
                ProgressUnits.PERCENT: f"{_('Percent'):>11}",
                ProgressUnits.LOADS: f"{_('Loads'):>12}",
                'Sticky': tk.E
                }
            }
        # By removing the carrier from here we remove it everywhere
        if not self.bgstally.fleet_carrier.available():
            del self.headings['Carrier']

        # UI components
        self.frame:tk.Frame = None
        self.frame_row:int = 0 # Row in the parent frame
        self.table_frame:tk.Frame = None # Table frame
        self.scrollbar:tk.Scrollbar = None # Scrollbar for the commodity list
        self.title:tk.Label = None # Title object
        self.colheadings:dict = {} # Column headings
        self.rows:list = []
        self.progvar:tk.IntVar = None
        self.progcols:dict = {} # Progress bar variables
        self.build_index:int = 0 # Which build we're showing
        self.view:ProgressView = ProgressView.REDUCED # Full, reduced, or no list of commodities
        self.comm_order:CommodityOrder = CommodityOrder.DEFAULT # Commodity order
        self.default_fg = None

    def create_frame(self, parent_frame:tk.Frame, start_row:int, column_count:int) -> None:
        ''' Create the progress frame '''
        try:
            self.colonisation = self.bgstally.colonisation
            tracked:dict = self.colonisation.get_tracked_builds()

            self.frame_row = start_row
            frame:tk.Frame = tk.Frame(parent_frame)
            frame.grid(row=start_row, column=0, columnspan=20, sticky=tk.EW)
            self.frame = frame

            row:int = 0; col:int = 0
            #ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=5, pady=2, sticky=tk.EW)
            #row += 1

            # Overall progress bar chart
            y=tk.LabelFrame(frame, border=1, height=10)
            y.grid(row=row, column=col, columnspan=5, pady=0, sticky=tk.EW)
            y.grid_rowconfigure(0, weight=1)
            y.grid_propagate(0)
            self.progvar = tk.IntVar()
            progbar:ttk.Progressbar = ttk.Progressbar(y, orient=tk.HORIZONTAL, variable=self.progvar, maximum=100, length=450, mode='determinate')
            progbar.grid(row=0, column=0, columnspan=20, pady=0, ipady=0, sticky=tk.EW)
            progbar.rowconfigure(0, weight=1)
            row += 1; col = 0

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
            ToolTip(prev_btn, text=_("Show previous build")) # LANG: tooltip for the previous build icon
            col += 1

            view_btn:tk.Label = tk.Label(frame, image=self.bgstally.ui.image_icon_change_view, cursor="hand2")
            view_btn.bind("<Button-1>", partial(self.event, "change"))
            view_btn.grid(row=row, column=col, sticky=tk.E)
            ToolTip(view_btn, text=_("Cycle commodity list order")) # LANG: tooltip for the commodity header
            col += 1

            next_btn:tk.Label = tk.Label(frame, image=self.bgstally.ui.image_icon_right_arrow, cursor="hand2")
            next_btn.bind("<Button-1>", partial(self.event, "next"))
            next_btn.grid(row=row, column=col, sticky=tk.E)
            ToolTip(next_btn, text=_("Show next build")) # LANG: tooltip for the next build icon
            row += 1; col = 0

            table_frame:tk.Frame = tk.Frame(frame)
            table_frame.columnconfigure(0, weight=1)
            table_frame.grid(row=row, column=col, columnspan=5, sticky=tk.NSEW)
            scr:tk.Scrollbar = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
            self.scrollbar = scr
            self.table_frame = table_frame

            # Column headings
            row = 0
            for i, (k, v) in enumerate(self.headings.items()):
                c = tk.Label(table_frame, text=_(v.get(ProgressUnits.TONNES)), cursor='hand2')
                c.grid(row=row, column=i, sticky=v.get('Sticky'))
                c.bind("<Button-1>", partial(self.change_view, k))
                c.config(foreground=config.get_str('dark_text') if config.get_int('theme') == 1 else 'black')
                ToolTip(c, text=_("Cycle commodity list filter views")) # LANG: tooltip for the column headings in the progress view indicating that clicking on the headings will cycle through the available views
                self.weight(c)
                self.colheadings[k] = c
            row += 1

            for i, col in enumerate(self.headings.keys()):
                # Progress bar chart
                if col == 'Commodity':
                    continue
                fr:tk.LabelFrame = tk.LabelFrame(table_frame, border=1, height=10, width=70)
                fr.grid(row=row, column=i, pady=0, sticky=tk.EW)
                fr.grid_rowconfigure(0, weight=1)
                fr.grid_propagate(0)

                self.progcols[col] = tk.IntVar()
                pbar:ttk.Progressbar = ttk.Progressbar(fr, orient=tk.HORIZONTAL, variable=self.progcols[col], maximum=100, length=70, mode='determinate', style='blue.Horizontal.TProgressbar')
                pbar.grid(row=0, column=i, pady=0, ipady=0, sticky=tk.EW)
            row += 1

            # Go through the complete list of possible commodities and make a row for each and hide it.
            for c in self.colonisation.get_commodity_list('All'):
                r:dict = {}

                for i, (col, val) in enumerate(self.headings.items()):
                    lbl:tk.Label = tk.Label(table_frame, text='')
                    lbl.grid(row=row, column=i, sticky=val.get('Sticky'))
                    if col == 'Commodity':
                        lbl.bind("<Button-1>", partial(self.link, c))
                        ToolTip(lbl, text=_("Click for Inara market")) # LANG: tooltip for the inara market commodity links
                        lbl.config(cursor='hand2', foreground=config.get_str('dark_text') if config.get_int('theme') == 1 else 'black')

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

            if len(tracked) == 0:
                Debug.logger.info("No tracked builds")
                frame.grid_remove()
                return

            if len(self.colonisation.get_required(tracked)) == 0:
                Debug.logger.info("No commodities to track")
                frame.grid_remove()
                return

            self.update_display()

        except Exception as e:
            Debug.logger.info(f"Error creating frame {e}")
            Debug.logger.error(traceback.format_exc())


    def event(self, event:str, tkEvent) -> None:
        ''' Process events from the buttons in the progress window. '''
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
                    self.view = ProgressView((self.view.value + 1) % len(ProgressView))
                    self.colonisation.save()
            self.update_display()

        except Exception as e:
            Debug.logger.info(f"Error processing event {e}")
            Debug.logger.error(traceback.format_exc())


    def change_view(self, column:str, tkEvent) -> None:
        ''' Change the view of the column when clicked. This is a toggle between tonnes, remaining, and loads. '''
        try:
            match column:
                case 'Commodity':
                    self.comm_order = CommodityOrder((self.comm_order.value + 1) % len(CommodityOrder))
                case _:
                    self.units[column] = ProgressUnits((self.units[column].value + 1) % (len(ProgressUnits)))
                    # Loads is meaningless for cargo!
                    if column == 'Cargo' and self.units[column] == ProgressUnits.LOADS:
                        self.units[column] = ProgressUnits((self.units[column].value + 1) % (len(ProgressUnits)))
                    # Percent is only meaningful for Delivered and Carrier
                    if column not in ['Delivered', 'Carrier'] and self.units[column] == ProgressUnits.PERCENT:
                        self.units[column] = ProgressUnits((self.units[column].value + 1) % (len(ProgressUnits)))
            self.update_display()

        except Exception as e:
            Debug.logger.info(f"Error processing link {e}")
            Debug.logger.error(traceback.format_exc())


    def link(self, comm:str, tkEvent) -> None:
        ''' Open the link to Inara for nearest location for the commodity. '''
        try:
            comm_id = self.colonisation.base_costs['All'].get(comm)
            sys:str = self.colonisation.current_system if self.colonisation.current_system != None else 'Sol'
            # pi3=3 - large, pi3=2 - medium
            size:int = 2 if self.colonisation.cargo_capacity < 407 else 3

            # pi7=5000 - supply (100, 500, 1000, 2500, 5000, 10000, 50000)
            tracked:dict = self.colonisation.get_tracked_builds()
            required:dict = self.colonisation.get_required(tracked)
            delivered:dict = self.colonisation.get_delivered(tracked)
            rem:int = (required[self.build_index].get(comm, 0) if len(required) > self.build_index else 0) - (delivered[self.build_index].get(comm, 0) if len(delivered) > self.build_index else 0)
            for min in [500, 1000, 2500, 5000, 10000, 50000]:
                if min > rem: break

            url:str = f"https://inara.cz/elite/commodities/?formbrief=1&pi1=1&pa1[]={comm_id}&ps1={quote(sys)}&pi10=3&pi11=0&pi3={size}&pi9=0&pi4=0&pi14=0&pi5=720&pi12=0&pi7={min}&pi8=0&pi13=0"
            webbrowser.open(url)

        except Exception as e:
            Debug.logger.info(f"Error processing link {e}")
            Debug.logger.error(traceback.format_exc())


    def update_display(self):
        ''' Main display update function. '''
        try:
            tracked:list = self.colonisation.get_tracked_builds()
            required:dict = self.colonisation.get_required(tracked)
            delivered:dict = self.colonisation.get_delivered(tracked)

            if len(tracked) == 0 or self.colonisation.cargo_capacity < 8:
                self.frame.grid_remove()
                Debug.logger.debug("No progress to display")
                return

            self.frame.grid(row=self.frame_row, column=0, columnspan=20, sticky=tk.EW)
            self.table_frame.grid(row=3, column=0, columnspan=5, sticky=tk.NSEW)

            # Set the build name (system name and plan name)
            name = _('All') # LANG: all builds
            if self.build_index < len(tracked):
                b:dict = tracked[self.build_index]
                bn:str = b.get('Name', '') if b.get('Name','') != '' else b.get('Base Type', '')
                pn:str = b.get('Plan', _('Unknown')) # Unknown system name
                name:str = ', '.join([pn, bn])

            self.title.config(text=name[-50:])

            # Hide the table but not the progress frame so the change view icon is still available
            if self.view == ProgressView.NONE:
                self.table_frame.grid_remove()
                Debug.logger.debug("No view, hiding table")
                return

            # Set the column headings according to the selected units
            totals:dict = {}
            for col in self.headings.keys():
                if col == 'Carrier' and not self.bgstally.fleet_carrier.available():
                    continue

                self.colheadings[col]['text'] = self.headings[col][self.units[col]]
                self.colheadings[col].grid()
                totals[col] = 0

            totals['Commodity'] = _("Total")  # LANG: total commodities

            # Go through each commodity and show or hide it as appropriate and display the appropriate values
            comms:list = []
            if self.colonisation.docked == True and self.colonisation.market != {} and self.comm_order == CommodityOrder.DEFAULT:
                comms = self.colonisation.get_commodity_list('All', CommodityOrder.CATEGORY)
            else:
                comms = self.colonisation.get_commodity_list('All', self.comm_order)

            if comms == None or comms == []:
                Debug.logger.info(f"No commodities found")
                return

            rc:int = 0
            for i, c in enumerate(comms):
                row:dict = self.rows[i]
                reqcnt:int = required[self.build_index].get(c, 0) if len(required) > self.build_index else 0
                delcnt:int = delivered[self.build_index].get(c, 0) if len(delivered) > self.build_index else 0
                remaining:int = reqcnt - delcnt

                cargo:int = self.colonisation.cargo.get(c, 0)
                carrier:int = self.colonisation.carrier_cargo.get(c, 0)
                tobuy:int = reqcnt - carrier - cargo

                #Debug.logger.debug(f"{name} {c} R:{reqcnt} D:{delcnt} r:{remaining} T:{tobuy} c:{cargo} C:{carrier}")
                if reqcnt > 0:
                    totals['Required'] += reqcnt
                    totals['Delivered'] += delcnt
                if remaining > 0:
                    totals['Cargo'] += cargo
                    if 'Carrier' in totals: totals['Carrier'] += carrier

                # We only show relevant (required) items. But.
                # If the view is reduced we don't show ones that are complete. Also.
                # If we're in minimal view we only show ones we still need to buy.
                if (reqcnt <= 0) or \
                    (remaining <= 0 and self.view != ProgressView.FULL) or \
                    (tobuy <= 0 and self.view == ProgressView.MINIMAL) or \
                    rc > MAX_ROWS:
                    for col in self.headings.keys():
                        row[col].grid_remove()
                    continue

                for col in self.headings.keys():
                    if col == 'Commodity':
                        # Shorten and display the commodity name
                        colstr:str = self.colonisation.commodities[c].get('Name', c)
                        if len(colstr) > 22: colstr = colstr[0:20] + '…'
                        row['Commodity']['text'] = colstr
                        row['Commodity'].bind("<Button-1>", partial(self.link, c))
                        row['Commodity'].grid()
                        continue

                    row[col]['text'] = self.get_value(col, reqcnt, delcnt, cargo, carrier)
                    row[col].grid()
                    self.highlight_row(row, c, reqcnt - delcnt)
                rc += 1
            
            self.display_totals(self.rows[i+1], tracked, totals)
            return

        except Exception as e:
            Debug.logger.info(f"Error updating display")
            Debug.logger.error(traceback.format_exc())


    def display_totals(self, row:dict, tracked:list, totals:dict) -> None:
        ''' Display the totals at the bottom of the table '''

        # We're down to having nothing left to deliver.
        if (totals['Required'] - totals['Delivered']) == 0:
            if len(tracked) == 1: # Nothing at all, remove the entire frame
                self.frame.grid_remove()
            else: # Just this one build? Hide the table
                self.table_frame.grid_remove()
            return

        for col in self.headings.keys():
            row[col]['text'] = self.get_value(col, totals['Required'], totals['Delivered'], totals['Cargo'], 0 if 'Carrier' not in totals else totals['Carrier']) if col != 'Commodity' else _("Total")
            self.weight(row[col])
            row[col].grid()

        # Update the progress graphs
        self.progvar.set(totals['Delivered'] * 100 / totals['Required'])
        self.progcols['Required'].set((totals['Required'] - totals['Delivered']) * 100 / totals['Required'])
        self.progcols['Delivered'].set(totals['Delivered'] * 100 / totals['Required'])
        self.progcols['Cargo'].set(totals['Cargo'] * 100 / self.colonisation.cargo_capacity)
        if (totals['Required'] - totals['Delivered']) > 0:
            # @TODO: Figure out carrier space for a better progress display
            self.progcols['Carrier'].set(totals['Carrier'] * 100 / (totals['Required'] - totals['Delivered']))
        return


    def get_value(self, column:str, required:int, delivered:int, cargo:int, carrier:int) -> str:
        ''' Calculate and format the commodity amount depending on the column and the units '''
        remaining:int = required - delivered

        match self.units[column]:
            case ProgressUnits.REMAINING if column == 'Required': valstr = f"{remaining:,}{_('t')}"
            case ProgressUnits.REMAINING if column == 'Delivered': valstr = f"{max(remaining-cargo-carrier, 0):,}{_('t')}"
            case ProgressUnits.REMAINING if column == 'Cargo': valstr = f"{max(remaining-cargo, 0):,}{_('t')}"
            case ProgressUnits.REMAINING if column == 'Carrier': valstr = f"{max(remaining-carrier,0):,}{_('t')}"

            case ProgressUnits.LOADS if column == 'Required':
                if ceil(remaining / self.colonisation.cargo_capacity) > 1:
                    valstr = f"{ceil(remaining / self.colonisation.cargo_capacity)}{_('L')}"
                else:
                    valstr = f"{remaining:,}{_('t')}"
            case ProgressUnits.LOADS if column == 'Delivered':
                if ceil(delivered / self.colonisation.cargo_capacity) > 1:
                    valstr = f"{ceil(delivered / self.colonisation.cargo_capacity)}{_('L')}"
                else:
                    valstr = f"{delivered:,}{_('t')}"
            case ProgressUnits.LOADS if column == 'Cargo': valstr = f"{ceil(cargo / self.colonisation.cargo_capacity)}{_('L')}"
            case ProgressUnits.LOADS if column == 'Carrier':
                if ceil(carrier / self.colonisation.cargo_capacity) > 1:
                    valstr = f"{ceil(carrier / self.colonisation.cargo_capacity)}{_('L')}"
                else:
                    valstr = f"{carrier:,}{_('t')}"
            case ProgressUnits.PERCENT if column == 'Required': valstr = f"{delivered * 100 / required:.0f}%"
            case ProgressUnits.PERCENT if column == 'Delivered': valstr = f"{delivered * 100 / required:.0f}%"
            case ProgressUnits.PERCENT if column == 'Cargo': valstr = f"{cargo * 100 / cargo:.0f}%"
            case ProgressUnits.PERCENT if column == 'Carrier': valstr = f"{carrier * 100 / required:.0f}%"

            case _ if column == 'Required': valstr = f"{required:,}{_('t')}"
            case _ if column == 'Delivered': valstr = f"{delivered:,}{_('t')}"
            case _ if column == 'Cargo': valstr = f"{cargo:,}{_('t')}"
            case _ if column == 'Carrier': valstr = f"{carrier:,}{_('t')}"
        return valstr


    def weight(self, item, w='bold') -> None:
        ''' Set font weight, defaults to bold '''
        fnt:tkFont.Font = tkFont.Font(font=item['font']).actual()
        item.configure(font=(fnt['family'], fnt['size'], w))


    def highlight_row(self, row:dict, c:str, qty:int = 0) -> None:
        ''' Color rows depending on the state '''
        tobuy:int = qty - self.colonisation.carrier_cargo.get(c, 0) - self.colonisation.cargo.get(c, 0)
        space:int = self.colonisation.cargo_capacity - sum(self.colonisation.cargo.values())

        for col in self.headings.keys():

            # Get the ed:mc default color
            row[col]['fg'] = config.get_str('dark_text') if config.get_int('theme') == 1 else 'black'
            self.weight(row[col], 'normal')

            if qty <= 0: # Nothing left to deliver, grey it out
                row[col]['fg'] = 'grey'; self.weight(row[col], 'normal')
                continue

            if qty <= self.colonisation.cargo.get(c, 0): # Have enough in our hold? green and bold
                row[col]['fg'] = 'green'; self.weight(row[col], 'bold')
                continue

            if tobuy <= 0 : # Gave enough between our hold and the carrier? green and normal
                row[col]['fg'] = 'green'; self.weight(row[col], 'normal')
                continue

            # What's available at this market?
            if self.colonisation.docked == True and self.colonisation.market.get(c, 0): # market!
                row[col]['fg'] = 'steelblue'
                # bold if need any and have room, otherwise normal
                self.weight(row[col], 'bold' if tobuy > 0 and space > 0 else 'normal')
                continue

        return
