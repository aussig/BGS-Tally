import json
from os import path, remove

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
            self.data = {
                'webhooks':
                    [
                        ["BGS", self.bgstally.state.DiscordBGSWebhook.get(), True, False, False, False, False],
                        ["TW", self.bgstally.state.DiscordTWWebhook.get(), False, True, False, False, False],
                        ["FC Materials", self.bgstally.state.DiscordFCMaterialsWebhook.get(), False, False, True, False, False],
                        ["FC Ops", self.bgstally.state.DiscordFCOperationsWebhook.get(), False, False, False, True, False],
                        ["CMDR Info", self.bgstally.state.DiscordCMDRInformationWebhook.get(), False, False, False, False, True]
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
