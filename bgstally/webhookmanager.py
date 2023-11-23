import json
from os import path, remove
from secrets import token_hex

from bgstally.constants import FOLDER_DATA
from bgstally.debug import Debug
from thirdparty.colors import *

FILENAME = "webhooks.json"


class WebhookManager:
    """
    Handle the user's Discord webhooks
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.data:dict = {}

        self.load()


    def load(self):
        """
        Load state from file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    self._from_dict(json.load(json_file))
            except Exception as e:
                Debug.logger.info(f"Unable to load {file}")

        if self.data == {}:
            # We are in default state, initialise from legacy data
            # List format: UUID, Nickname, URL, BGS, TW, FC Mats, FC Ops, CMDR
            self.data = {
                'webhooks':
                    [
                        [token_hex(9), "BGS", self.bgstally.state.DiscordBGSWebhook.get(), True, False, False, False, False],
                        [token_hex(9), "TW", self.bgstally.state.DiscordTWWebhook.get(), False, True, False, False, False],
                        [token_hex(9), "FC Materials", self.bgstally.state.DiscordFCMaterialsWebhook.get(), False, False, True, False, False],
                        [token_hex(9), "FC Ops", self.bgstally.state.DiscordFCOperationsWebhook.get(), False, False, False, True, False],
                        [token_hex(9), "CMDR Info", self.bgstally.state.DiscordCMDRInformationWebhook.get(), False, False, False, False, True]
                    ]
            }


    def save(self):
        """
        Save state to file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile)


    def set_webhooks(self, data: list):
        """
        Store the latest webhooks data
        """
        if data is None:
            self.data['webhooks'] = []
            return

        for webhook in data:
            # Set UUID if not already set (a new entry in the list)
            if webhook[0] is None or webhook[0] == "": webhook[0] = token_hex(9)

        self.data['webhooks'] = data
        self.save()


    def get_webhooks(self) -> list:
        """
        Return the latest webhooks data
        """
        return self.data.get('webhooks', [])


    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return self.data


    def _from_dict(self, dict: dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.data = dict
