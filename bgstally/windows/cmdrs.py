import tkinter as tk
from datetime import datetime
from functools import partial
from tkinter import ttk
from urllib.parse import quote

from ttkHyperlinkLabel import HyperlinkLabel

from bgstally.constants import COLOUR_HEADING_1, DATETIME_FORMAT_JOURNAL, FONT_HEADING_1, FONT_HEADING_2, CmdrInteractionReason, DiscordChannel
from bgstally.debug import Debug
from bgstally.utils import _, __
from bgstally.widgets import TreeviewPlus
from thirdparty.colors import *

DATETIME_FORMAT_CMDRLIST = "%Y-%m-%d %H:%M:%S"


class WindowCMDRs:
    """
    Handles the CMDR list window
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.selected_cmdr:dict = None
        self.selected_items:list = None
        self.target_data:list = None
        self.toplevel:tk.Toplevel = None


    def show(self):
        """
        Show our window
        """
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            return

        self.toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.toplevel.title(_("{plugin_name} - CMDR Interactions").format(plugin_name=self.bgstally.plugin_name)) # LANG: CMDR window title
        self.toplevel.geometry("1200x800")

        container_frame = ttk.Frame(self.toplevel)
        container_frame.pack(fill=tk.BOTH, expand=1)

        list_frame = ttk.Frame(container_frame)
        list_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=1)

        buttons_frame = ttk.Frame(container_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        details_frame = ttk.Frame(container_frame)
        details_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

        column_info = [{'title': _("Name"), 'type': "name", 'align': tk.W, 'stretch': tk.YES, 'width': 200}, # LANG: CMDR window column title
                        {'title': _("System"), 'type': "name", 'align': tk.W, 'stretch': tk.YES, 'width': 200}, # LANG: CMDR window column title
                        {'title': _("Squadron ID"), 'type': "name", 'align': tk.CENTER, 'stretch': tk.NO, 'width': 50}, # LANG: CMDR window column title
                        {'title': _("Ship"), 'type': "name", 'align': tk.W, 'stretch': tk.YES, 'width': 200}, # LANG: CMDR window column title
                        {'title': _("Legal"), 'type': "name", 'align': tk.W, 'stretch': tk.NO, 'width': 60}, # LANG: CMDR window column title
                        {'title': _("Date / Time"), 'type': "datetime", 'align': tk.CENTER, 'stretch': tk.NO, 'width': 150}, # LANG: CMDR window column title
                        {'title': _("Interaction"), 'type': "name", 'align': tk.W, 'stretch': tk.YES, 'width': 300}] # LANG: CMDR window column title
        self.target_data = self.bgstally.target_log.get_targetlog()

        treeview = TreeviewPlus(list_frame, columns=[d['title'] for d in column_info], show="headings", callback=self._cmdr_selected, datetime_format=DATETIME_FORMAT_CMDRLIST)
        treeview.bind('<<TreeviewSelect>>', partial(self._cmdr_selection_changed, treeview))
        vsb = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=treeview.yview)
        vsb.pack(fill=tk.Y, side=tk.RIGHT)
        treeview.configure(yscrollcommand=vsb.set)
        treeview.pack(fill=tk.BOTH, expand=1)

        current_row = 0
        ttk.Label(details_frame, text=_("CMDR Details"), font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).grid(row=current_row, column=0, sticky=tk.W); current_row += 1 # LANG: Label on CMDR window
        ttk.Label(details_frame, text=_("Name: "), font=FONT_HEADING_2).grid(row=current_row, column=0, sticky=tk.W) # LANG: Label on CMDR window
        self.cmdr_details_name = ttk.Label(details_frame, text="")
        self.cmdr_details_name.grid(row=current_row, column=1, sticky=tk.W)
        ttk.Label(details_frame, text=_("Inara: "), font=FONT_HEADING_2).grid(row=current_row, column=2, sticky=tk.W) # LANG: Label on CMDR window
        self.cmdr_details_name_inara = HyperlinkLabel(details_frame, text="", url="https://inara.cz/elite/cmdrs/?search=aussi", underline=True)
        self.cmdr_details_name_inara.grid(row=current_row, column=3, sticky=tk.W); current_row += 1
        ttk.Label(details_frame, text=_("Squadron: "), font=FONT_HEADING_2).grid(row=current_row, column=0, sticky=tk.W) # LANG: Label on CMDR window
        self.cmdr_details_squadron = ttk.Label(details_frame, text="")
        self.cmdr_details_squadron.grid(row=current_row, column=1, sticky=tk.W)
        ttk.Label(details_frame, text=_("Inara: "), font=FONT_HEADING_2).grid(row=current_row, column=2, sticky=tk.W) # LANG: Label on CMDR window
        self.cmdr_details_squadron_inara = HyperlinkLabel(details_frame, text="", url="https://inara.cz/elite/squadrons-search/?search=ghst", underline=True)
        self.cmdr_details_squadron_inara.grid(row=current_row, column=3, sticky=tk.W); current_row += 1
        ttk.Label(details_frame, text=_("Interaction: "), font=FONT_HEADING_2).grid(row=current_row, column=0, sticky=tk.W) # LANG: Label on CMDR window
        self.cmdr_details_interaction = ttk.Label(details_frame, text="")
        self.cmdr_details_interaction.grid(row=current_row, column=1, sticky=tk.W); current_row += 1

        for column in column_info:
            treeview.heading(column['title'], text=column['title'].title(), sort_by=column['type'])
            treeview.column(column['title'], anchor=column['align'], stretch=column['stretch'], width=column['width'])

        for target in reversed(self.target_data):
            target_values = [target.get('TargetName', "----"), \
                             target.get('System', "----"), \
                             target.get('SquadronID', "----"), \
                             target.get('Ship', "----"), \
                             target.get('LegalStatus', "----"), \
                             datetime.strptime(target['Timestamp'], DATETIME_FORMAT_JOURNAL).strftime(DATETIME_FORMAT_CMDRLIST), \
                             self._get_human_readable_reason(target.get('Reason'), False)]
            treeview.insert("", 'end', values=target_values, iid=target.get('index'))

        self.post_button = tk.Button(buttons_frame, text=_("Post CMDR to Discord"), command=partial(self._post_to_discord)) # LANG: Button on CMDR window
        self.post_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.post_button['state'] = tk.DISABLED

        self.delete_button = tk.Button(buttons_frame, text=_("Delete Selected"), bg="red", fg="white", command=partial(self._delete_selected, treeview)) # LANG: Button on CMDR window
        self.delete_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.delete_button['state'] = tk.DISABLED


    def _cmdr_selected(self, values, column, treeview:TreeviewPlus, iid:str):
        """
        A CMDR row has been clicked in the list, show details
        """
        self.cmdr_details_name.config(text = "")
        self.cmdr_details_name_inara.configure(text = "", url = "")
        self.cmdr_details_squadron.config(text = "")
        self.cmdr_details_squadron_inara.configure(text = "", url = "")
        self.cmdr_details_interaction.configure(text = "")

        # Fetch the info for this CMDR. iid is the index into the original (unsorted) CMDR list.
        self.selected_cmdr = self.target_data[int(iid)]

        if 'TargetName' in self.selected_cmdr: self.cmdr_details_name.config(text=self.selected_cmdr.get('TargetName'))
        if 'inaraURL' in self.selected_cmdr: self.cmdr_details_name_inara.configure(text=_("Inara Info Available ⤴"), url=self.selected_cmdr.get('inaraURL')) # LANG: Inara URL on CMDR window
        if 'squadron' in self.selected_cmdr:
            squadron_info = self.selected_cmdr.get('squadron')
            if 'squadronName' in squadron_info: self.cmdr_details_squadron.config(text=f"{squadron_info.get('squadronName')} ({squadron_info.get('squadronMemberRank')})")
            if 'inaraURL' in squadron_info: self.cmdr_details_squadron_inara.configure(text=_("Inara Info Available ⤴"), url=squadron_info.get('inaraURL')) # LANG: Inara URL on CMDR window
        elif 'SquadronID' in self.selected_cmdr:
            self.cmdr_details_squadron.config(text=f"{self.selected_cmdr.get('SquadronID')}")
        self.cmdr_details_interaction.config(text=self._get_human_readable_reason(self.selected_cmdr.get('Reason'), False))


    def _cmdr_selection_changed(self, treeview:TreeviewPlus, *args):
        """
        The selected CMDRs have changed in the list. Called on any change, so there could be nothing selected, one CMDR selected
        or multiple CMDRs.

        Args:
            treeview (TreeviewPlus): The TreeViewPlus object
        """
        self.selected_items = treeview.selection()

        if len(self.selected_items) == 1 and self.bgstally.discord.valid_webhook_available(DiscordChannel.CMDR_INFORMATION):
            self.post_button.configure(text=_("Post CMDR to Discord")) # LANG: Button on CMDR window
            self.post_button['state'] = tk.NORMAL
            self.delete_button['state'] = tk.NORMAL
        elif len(self.selected_items) > 1 and self.bgstally.discord.valid_webhook_available(DiscordChannel.CMDR_INFORMATION):
            self.post_button.configure(text=_("Post CMDR List to Discord")) # LANG: Button on CMDR window
            self.post_button['state'] = tk.NORMAL
            self.delete_button['state'] = tk.NORMAL
        else:
            self.post_button.configure(text=_("Post CMDR to Discord")) # LANG: Button on CMDR window
            self.post_button['state'] = tk.DISABLED
            self.delete_button['state'] = tk.DISABLED


    def _delete_selected(self, treeview:TreeviewPlus):
        """
        Delete the currently selected CMDRs
        """
        selected_items:list = treeview.selection()
        for selected_iid in selected_items:
           for i in range(len(self.target_data)):
               if int(self.target_data[i]['index']) == int(selected_iid):
                   self.target_data.pop(i) # Remove the corresponding item
                   break
           treeview.delete(int(selected_iid))

        self.selected_cmdr = None
        self._cmdr_selection_changed(treeview)


    def _post_to_discord(self):
        """
        Post the current selected CMDR or multiple CMDR details to discord
        """
        self.post_button.config(state=tk.DISABLED)

        if len(self.selected_items) == 1 and self.bgstally.discord.valid_webhook_available(DiscordChannel.CMDR_INFORMATION):
            self._post_single_cmdr_to_discord()
        elif len(self.selected_items) > 1 and self.bgstally.discord.valid_webhook_available(DiscordChannel.CMDR_INFORMATION):
            self._post_multiple_CMDRs_to_discord()

        self.post_button.after(5000, self._enable_post_button)


    def _enable_post_button(self):
        """
        Re-enable the post to discord button if it should be enabled
        """
        self.post_button.config(state=(tk.NORMAL if self.bgstally.discord.valid_webhook_available(DiscordChannel.CMDR_INFORMATION) else tk.DISABLED))


    def _post_single_cmdr_to_discord(self):
        """
        Post the current selected cmdr details to discord
        """
        if not self.selected_cmdr: return

        embed_fields = [
            {
                "name": __("Name"), # LANG: Discord heading
                "value": self.selected_cmdr.get('TargetName'),
                "inline": True
            },
            {
                "name": __("In System"), # LANG: Discord heading
                "value": self.selected_cmdr.get('System'),
                "inline": True
            },
            {
                "name": __("In Ship"), # LANG: Discord heading
                "value": self.selected_cmdr.get('Ship'),
                "inline": True
            },
            {
                "name": __("In Squadron"), # LANG: Discord heading
                "value": self.selected_cmdr.get('SquadronID'),
                "inline": True
            },
            {
                "name": __("Legal Status"), # LANG: Discord heading
                "value": self.selected_cmdr.get('LegalStatus'),
                "inline": True
            },
            {
                "name": __("Date and Time"), # LANG: Discord heading
                "value": datetime.strptime(self.selected_cmdr.get('Timestamp'), DATETIME_FORMAT_JOURNAL).strftime(DATETIME_FORMAT_CMDRLIST),
                "inline": True
            }
        ]

        if 'inaraURL' in self.selected_cmdr:
            embed_fields.append({
                "name": __("CMDR Inara Link"), # LANG: Discord heading
                "value": f"[{self.selected_cmdr.get('TargetName')}]({self.selected_cmdr.get('inaraURL')})",
                "inline": True
                })

        if 'squadron' in self.selected_cmdr:
            squadron_info = self.selected_cmdr.get('squadron')
            if 'squadronName' in squadron_info and 'inaraURL' in squadron_info:
                embed_fields.append({
                    "name": __("Squadron Inara Link"), # LANG: Discord heading
                    "value": f"[{squadron_info.get('squadronName')} ({squadron_info.get('squadronMemberRank')})]({squadron_info.get('inaraURL')})",
                    "inline": True
                    })

        description = f"```ansi\n{self._get_human_readable_reason(self.selected_cmdr.get('Reason'), True)}\n```"

        self.bgstally.discord.post_embed(f"CMDR {self.selected_cmdr.get('TargetName')}", description, embed_fields, None, DiscordChannel.CMDR_INFORMATION, None)


    def _post_multiple_CMDRs_to_discord(self):
        """
        Post the currently selected list of CMDRs to discord
        """
        text:str = ""

        for selected_iid in self.selected_items:
            if len(text) > 1500:
                text += "[...]"
                break

            for cmdr in self.target_data:
                if int(cmdr['index']) == int(selected_iid):
                    text += f"{datetime.strptime(cmdr.get('Timestamp'), DATETIME_FORMAT_JOURNAL).strftime(DATETIME_FORMAT_CMDRLIST)}: "

                    if 'inaraURL' in cmdr:
                        text += f" - [{cmdr.get('TargetName')}](<{cmdr.get('inaraURL')}>)"
                    else:
                        text += f" - {cmdr.get('TargetName')}"

                    text += f" - [{cmdr.get('System')}](<https://inara.cz/elite/starsystem/?search={quote(cmdr.get('System'))}>) - {cmdr.get('Ship')}"

                    if 'squadron' in cmdr:
                        squadron_info = cmdr.get('squadron')
                        if 'squadronName' in squadron_info and 'inaraURL' in squadron_info:
                            text += f" - [{squadron_info.get('squadronName')}](<{squadron_info.get('inaraURL')}>)"
                    text += "\n"

        self.bgstally.discord.post_plaintext(text, None, DiscordChannel.CMDR_INFORMATION, None)


    def _get_human_readable_reason(self, reason:CmdrInteractionReason, discord:bool) -> str:
        """
        Get a human readable version of this interaction reason

        Args:
            reason (CmdrInteractionReason): The interaction reason
            discord (bool): True if this message is going to Discord. Defaults to False.

        Returns:
            str: Descriptive text for reason
        """

        match reason:
            case CmdrInteractionReason.FRIEND_REQUEST_RECEIVED:
                if discord:
                    return cyan(__("Friend request received from this CMDR")) # LANG: Discord CMDR information
                else:
                    return _("Received friend request from") # LANG: CMDR information
            case CmdrInteractionReason.FRIEND_ADDED:
                if discord:
                    return cyan(__("This CMDR was added as a friend")) # LANG: Discord CMDR information
                else:
                    return _("Added a friend") # LANG: CMDR information
            case CmdrInteractionReason.INTERDICTED_BY:
                if discord:
                    return red(__("INTERDICTED BY this CMDR")) # LANG: Discord CMDR information
                else:
                    return _("Interdicted by") # LANG: CMDR information
            case CmdrInteractionReason.KILLED_BY:
                if discord:
                    return red(__("KILLED BY this CMDR")) # LANG: Discord CMDR information
                else:
                    return _("Killed by") # LANG: CMDR information
            case CmdrInteractionReason.MESSAGE_RECEIVED:
                if discord:
                    return blue(__("Message received from this CMDR in local chat")) # LANG: Discord CMDR information
                else:
                    return _("Received message from") # LANG: CMDR information
            case CmdrInteractionReason.TEAM_INVITE_RECEIVED:
                if discord:
                    return green(__("Team invite received from this CMDR")) # LANG: Discord CMDR information
                else:
                    return _("Received team invite from") # LANG: CMDR information
            case _:
                if discord:
                    return yellow(__("I scanned this CMDR")) # LANG: Discord CMDR information
                else:
                    return _("Scanned") # LANG: CMDR information
