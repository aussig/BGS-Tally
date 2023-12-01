import json
from os import path, remove
from secrets import token_hex

from bgstally.constants import DiscordChannel, FOLDER_DATA
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
                        {'uuid': token_hex(9), 'name': "BGS", 'url': self.bgstally.state.DiscordBGSWebhook.get(),
                         DiscordChannel.BGS: True, DiscordChannel.THARGOIDWAR: False, DiscordChannel.FLEETCARRIER_MATERIALS: False,
                         DiscordChannel.FLEETCARRIER_OPERATIONS: False, DiscordChannel.CMDR_INFORMATION: False},
                        {'uuid': token_hex(9), 'name': "TW", 'url': self.bgstally.state.DiscordTWWebhook.get(),
                         DiscordChannel.BGS: False, DiscordChannel.THARGOIDWAR: True, DiscordChannel.FLEETCARRIER_MATERIALS: False,
                         DiscordChannel.FLEETCARRIER_OPERATIONS: False, DiscordChannel.CMDR_INFORMATION: False},
                        {'uuid': token_hex(9), 'name': "FC Materials", 'url': self.bgstally.state.DiscordFCMaterialsWebhook.get(),
                         DiscordChannel.BGS: False, DiscordChannel.THARGOIDWAR: False, DiscordChannel.FLEETCARRIER_MATERIALS: True,
                         DiscordChannel.FLEETCARRIER_OPERATIONS: False, DiscordChannel.CMDR_INFORMATION: False},
                        {'uuid': token_hex(9), 'name': "FC Ops", 'url': self.bgstally.state.DiscordFCOperationsWebhook.get(),
                         DiscordChannel.BGS: False, DiscordChannel.THARGOIDWAR: False, DiscordChannel.FLEETCARRIER_MATERIALS: False,
                         DiscordChannel.FLEETCARRIER_OPERATIONS: True, DiscordChannel.CMDR_INFORMATION: False},
                        {'uuid': token_hex(9), 'name': "CMDR Info", 'url': self.bgstally.state.DiscordCMDRInformationWebhook.get(),
                         DiscordChannel.BGS: False, DiscordChannel.THARGOIDWAR: False, DiscordChannel.FLEETCARRIER_MATERIALS: False,
                         DiscordChannel.FLEETCARRIER_OPERATIONS: False, DiscordChannel.CMDR_INFORMATION: True}
                    ]
            }


    def save(self):
        """
        Save state to file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile)


    def set_webhooks_from_list(self, data: list):
        """
        Store webhooks data from a list of lists

        Args:
            data (list): A list containing the webhooks, each webhook being a list
        """
        self.data['webhooks'] = []

        if data is None or data == []:
            self.save()
            return

        for webhook in data:
            if len(webhook) == 8:
                self.data['webhooks'].append({
                    'uuid': webhook[0] if webhook[0] is not None and webhook[0] != "" else token_hex(9),
                    'name': webhook[1],
                    'url': webhook[2],
                    DiscordChannel.BGS: webhook[3],
                    DiscordChannel.THARGOIDWAR: webhook[4],
                    DiscordChannel.FLEETCARRIER_MATERIALS: webhook[5],
                    DiscordChannel.FLEETCARRIER_OPERATIONS: webhook[6],
                    DiscordChannel.CMDR_INFORMATION: webhook[7]
                })

        self.save()


    def get_webhooks_as_dict(self, channel:DiscordChannel|None = None) -> list:
        """
        Get the webhooks as a dict

        Args:
            channel (DiscordChannel | None, optional): If None or omitted, return all webhooks. If specified, only return webhooks for the given channel. Defaults to None.

        Returns:
            dict: A dict containing the relevant webhooks, with the key being the uuid and the value being the webhook as a dict
        """
        result:dict = {}

        for webhook in self.data.get('webhooks', []):
            if channel is None or webhook.get(channel) == True:
                uuid:str = webhook.get('uuid', token_hex(9))
                result[uuid] = webhook

        return result


    def get_webhooks_as_list(self, channel:DiscordChannel|None = None) -> list:
        """
        Get the webhooks as a list of lists

        Args:
            channel (DiscordChannel | None, optional): If None or omitted, return all webhooks. If specified, only return webhooks for the given channel. Defaults to None.

        Returns:
            list: A list containing the relevant webhooks, each webhook being a list
        """
        result:list = []

        for webhook in self.data.get('webhooks', []):
            if channel is None or webhook.get(channel) == True:
                result.append([
                    webhook.get('uuid', token_hex(9)),
                    webhook.get('name', ""),
                    webhook.get('url', ""),
                    webhook.get(DiscordChannel.BGS, False),
                    webhook.get(DiscordChannel.THARGOIDWAR, False),
                    webhook.get(DiscordChannel.FLEETCARRIER_MATERIALS, False),
                    webhook.get(DiscordChannel.FLEETCARRIER_OPERATIONS, False),
                    webhook.get(DiscordChannel.CMDR_INFORMATION, False)
                ])

        return result


    def _as_dict(self) -> dict:
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return self.data


    def _from_dict(self, dict: dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.data = dict
