import tkinter as tk
from datetime import datetime
from functools import partial
from tkinter import ttk

from bgstally.constants import DATETIME_FORMAT_JOURNAL, DiscordChannel, FONT_HEADING
from bgstally.debug import Debug
from ttkHyperlinkLabel import HyperlinkLabel

DATETIME_FORMAT_CMDRLIST = "%Y-%m-%d %H:%M:%S"


class WindowCMDRs:
    """
    Handles the CMDR list window
    """

    def __init__(self, bgstally, ui):
        self.bgstally = bgstally
        self.ui = ui

        self.selected_cmdr = None
        self.toplevel:tk.Toplevel = None


    def show(self):
        """
        Show our window
        """
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            return

        self.toplevel = tk.Toplevel(self.ui.frame)
        self.toplevel.title("Targeted CMDR Information")
        self.toplevel.geometry("1200x800")

        container_frame = ttk.Frame(self.toplevel)
        container_frame.pack(fill=tk.BOTH, expand=1)

        list_frame = ttk.Frame(container_frame)
        list_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=1)

        buttons_frame = ttk.Frame(container_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        details_frame = ttk.Frame(container_frame)
        details_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        column_info = [{'title': "Name", 'type': "name", 'align': tk.W, 'stretch': tk.YES, 'width': 200},
                        {'title': "System", 'type': "name", 'align': tk.W, 'stretch': tk.YES, 'width': 200},
                        {'title': "Squadron ID", 'type': "name", 'align': tk.CENTER, 'stretch': tk.NO, 'width': 50},
                        {'title': "Ship", 'type': "name", 'align': tk.W, 'stretch': tk.YES, 'width': 200},
                        {'title': "Legal", 'type': "name", 'align': tk.W, 'stretch': tk.NO, 'width': 60},
                        {'title': "Date / Time", 'type': "datetime", 'align': tk.CENTER, 'stretch': tk.NO, 'width': 150}]
        target_data = self.bgstally.target_log.get_targetlog()

        treeview = TreeviewPlus(list_frame, columns=[d['title'] for d in column_info], show="headings", callback=self._cmdr_selected)
        vsb = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=treeview.yview)
        vsb.pack(fill=tk.Y, side=tk.RIGHT)
        treeview.configure(yscrollcommand=vsb.set)
        treeview.pack(fill=tk.BOTH, expand=1)

        current_row = 0
        ttk.Label(details_frame, text="CMDR Details", font=FONT_HEADING).grid(row=current_row, column=0, sticky=tk.W); current_row += 1
        ttk.Label(details_frame, text="Name: ", font=FONT_HEADING).grid(row=current_row, column=0, sticky=tk.W)
        self.cmdr_details_name = ttk.Label(details_frame, text="")
        self.cmdr_details_name.grid(row=current_row, column=1, sticky=tk.W)
        ttk.Label(details_frame, text="Inara: ", font=FONT_HEADING).grid(row=current_row, column=2, sticky=tk.W)
        self.cmdr_details_name_inara = HyperlinkLabel(details_frame, text="", url="https://inara.cz/elite/cmdrs/?search=aussi", underline=True)
        self.cmdr_details_name_inara.grid(row=current_row, column=3, sticky=tk.W); current_row += 1
        ttk.Label(details_frame, text="Squadron: ", font=FONT_HEADING).grid(row=current_row, column=0, sticky=tk.W)
        self.cmdr_details_squadron = ttk.Label(details_frame, text="")
        self.cmdr_details_squadron.grid(row=current_row, column=1, sticky=tk.W)
        ttk.Label(details_frame, text="Inara: ", font=FONT_HEADING).grid(row=current_row, column=2, sticky=tk.W)
        self.cmdr_details_squadron_inara = HyperlinkLabel(details_frame, text="", url="https://inara.cz/elite/squadrons-search/?search=ghst", underline=True)
        self.cmdr_details_squadron_inara.grid(row=current_row, column=3, sticky=tk.W); current_row += 1

        for column in column_info:
            treeview.heading(column['title'], text=column['title'].title(), sort_by=column['type'])
            treeview.column(column['title'], anchor=column['align'], stretch=column['stretch'], width=column['width'])

        for target in reversed(target_data):
            target_values = [target['TargetName'], target['System'], target['SquadronID'], target.get('ShipLocalised', target['Ship']), target['LegalStatus'], datetime.strptime(target['Timestamp'], DATETIME_FORMAT_JOURNAL).strftime(DATETIME_FORMAT_CMDRLIST)]
            treeview.insert("", 'end', values=target_values)

        if self.bgstally.discord.is_webhook_valid(DiscordChannel.BGS):
            self.post_button =ttk.Button(buttons_frame, text="Post to Discord", command=partial(self._post_to_discord))
            self.post_button.pack(side=tk.RIGHT, padx=5, pady=5)
            self.post_button['state'] = tk.DISABLED


    def _cmdr_selected(self, values, column):
        """
        A CMDR row has been clicked in the list, show details
        """
        self.cmdr_details_name.config(text = "")
        self.cmdr_details_name_inara.configure(text = "", url = "")
        self.cmdr_details_squadron.config(text = "")
        self.cmdr_details_squadron_inara.configure(text = "", url = "")

        # Fetch the latest info for this CMDR
        self.selected_cmdr = self.bgstally.target_log.get_target_info(values[0])
        if not self.selected_cmdr: return

        if 'TargetName' in self.selected_cmdr: self.cmdr_details_name.config(text = self.selected_cmdr['TargetName'])
        if 'inaraURL' in self.selected_cmdr: self.cmdr_details_name_inara.configure(text = "Inara Info Available", url = self.selected_cmdr['inaraURL'])
        if 'squadron' in self.selected_cmdr:
            squadron_info = self.selected_cmdr['squadron']
            if 'squadronName' in squadron_info: self.cmdr_details_squadron.config(text = f"{squadron_info['squadronName']} ({squadron_info['squadronMemberRank']})")
            if 'inaraURL' in squadron_info: self.cmdr_details_squadron_inara.configure(text = "Inara Info Available", url = squadron_info['inaraURL'])
        elif 'SquadronID' in self.selected_cmdr:
            self.cmdr_details_squadron.config(text = f"{self.selected_cmdr['SquadronID']}")

        self.post_button['state'] = tk.NORMAL


    def _post_to_discord(self):
        """
        Post the current selected cmdr details to discord
        """
        if not self.selected_cmdr: return

        embed_fields = [
            {
                "name": "Name",
                "value": self.selected_cmdr['TargetName'],
                "inline": True
            },
            {
                "name": "Spotted in System",
                "value": self.selected_cmdr['System'],
                "inline": True
            },
            {
                "name": "In Ship",
                "value": self.selected_cmdr.get('ShipLocalised', self.selected_cmdr['Ship']),  # More recently we store both, but only 'Ship' may be present for old data
                "inline": True
            },
            {
                "name": "In Squadron",
                "value": self.selected_cmdr['SquadronID'],
                "inline": True
            },
            {
                "name": "Legal Status",
                "value": self.selected_cmdr['LegalStatus'],
                "inline": True
            },
            {
                "name": "Date and Time",
                "value": datetime.strptime(self.selected_cmdr['Timestamp'], DATETIME_FORMAT_JOURNAL).strftime(DATETIME_FORMAT_CMDRLIST),
                "inline": True
            }
        ]

        if 'inaraURL' in self.selected_cmdr:
            embed_fields.append({
                "name": "CMDR Inara Link",
                "value": f"[{self.selected_cmdr['TargetName']}]({self.selected_cmdr['inaraURL']})",
                "inline": True
                })

        if 'squadron' in self.selected_cmdr:
            squadron_info = self.selected_cmdr['squadron']
            if 'squadronName' in squadron_info and 'inaraURL' in squadron_info:
                embed_fields.append({
                    "name": "Squadron Inara Link",
                    "value": f"[{squadron_info['squadronName']} ({squadron_info['squadronMemberRank']})]({squadron_info['inaraURL']})",
                    "inline": True
                    })

        self.bgstally.discord.post_embed(f"CMDR {self.selected_cmdr['TargetName']} Spotted", None, embed_fields, None, DiscordChannel.BGS, None)


class TreeviewPlus(ttk.Treeview):
    def __init__(self, parent, callback, *args, **kwargs):
        ttk.Treeview.__init__(self, parent, *args, **kwargs)
        self.callback = callback
        self.bind('<ButtonRelease-1>', self._select_item)


    def heading(self, column, sort_by=None, **kwargs):
        if sort_by and not hasattr(kwargs, 'command'):
            func = getattr(self, f"_sort_by_{sort_by}", None)
            if func:
                kwargs['command'] = partial(func, column, False)

        return super().heading(column, **kwargs)

    def _select_item(self, event):
        clicked_item = self.item(self.focus())
        clicked_column_ref = self.identify_column(event.x)
        if type(clicked_item['values']) is not list: return

        clicked_column = int(clicked_column_ref[1:]) - 1
        if clicked_column < 0: return

        self.callback(clicked_item['values'], clicked_column)

    def _sort(self, column, reverse, data_type, callback):
        l = [(self.set(k, column), k) for k in self.get_children('')]
        l.sort(key=lambda t: data_type(t[0]), reverse=reverse)
        for index, (_, k) in enumerate(l):
            self.move(k, '', index)

        self.heading(column, command=partial(callback, column, not reverse))

    def _sort_by_num(self, column, reverse):
        self._sort(column, reverse, int, self._sort_by_num)

    def _sort_by_name(self, column, reverse):
        self._sort(column, reverse, str, self._sort_by_name)

    def _sort_by_datetime(self, column, reverse):
        def _str_to_datetime(string):
            return datetime.strptime(string, DATETIME_FORMAT_CMDRLIST)

        self._sort(column, reverse, _str_to_datetime, self._sort_by_datetime)

