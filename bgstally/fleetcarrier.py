import json
from datetime import datetime
from os import path, remove

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_DATA, DiscordChannel, MaterialsCategory
from bgstally.debug import Debug
from bgstally.discord import DATETIME_FORMAT
from thirdparty.colors import *

FILENAME = "fleetcarrier.json"


class FleetCarrier:
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.data:dict = {}
        self.name:str = None
        self.callsign:str = None
        self.onfoot_mats_selling:list = []
        self.onfoot_mats_buying:list = []

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


    def save(self):
        """
        Save state to file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self._as_dict(), outfile)


    def available(self):
        """
        Return true if there is data available on a Fleet Carrier
        """
        return self.name is not None and self.callsign is not None


    def update(self, data: dict):
        """
        Store the latest data
        """
        # Data directly from CAPI response. Structure documented here:
        # https://github.com/Athanasius/fd-api/blob/main/docs/FrontierDevelopments-CAPI-endpoints.md#fleetcarrier

        # Store the whole data structure
        self.data = data

        # Name is encoded as hex string
        self.name = bytes.fromhex(self.data.get('name', {}).get('vanityName', "----")).decode('utf-8')
        self.callsign = self.data.get('name', {}).get('callsign', "----")

        # Sort sell orders - a Dict of Dicts
        materials: dict = self.data.get('orders', {}).get('onfootmicroresources', {}).get('sales')
        if materials is not None:
            self.onfoot_mats_selling = sorted(materials.values(), key=lambda x: x['locName'])

        # Sort buy orders - a List of Dicts
        materials = self.data.get('orders', {}).get('onfootmicroresources', {}).get('purchases')
        if materials is not None:
            self.onfoot_mats_buying = sorted(materials, key=lambda x: x['locName'])


    def stats_received(self, journal_entry: dict):
        """
        The user entered the carrier management screen
        """
        if self.name is None:
            self.name = journal_entry.get("Name")
            self.callsign = journal_entry.get("Callsign")
            self.data['dockingAccess'] = journal_entry.get("DockingAccess")


    def jump_requested(self, journal_entry: dict):
        """
        The user scheduled a carrier jump
        """
        # {"timestamp": "2020-04-20T09:30:58Z", "event": "CarrierJumpRequest", "CarrierID": 3700005632, "SystemName": "Paesui Xena", "Body": "Paesui Xena A", "SystemAddress": 7269634680241, "BodyID": 1, "DepartureTime":"2020-04-20T09:45:00Z"}

        title:str = f"Jump Scheduled for Carrier {self.name}"

        fields = []
        fields.append({'name': "From System", 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True})
        fields.append({'name': "To System", 'value': journal_entry.get('SystemName', "Unknown"), 'inline': True})
        fields.append({'name': "To Body", 'value': journal_entry.get('Body', "Unknown"), 'inline': True})
        fields.append({'name': "Departure Time", 'value': datetime.strptime(journal_entry.get('DepartureTime'), DATETIME_FORMAT_JOURNAL).strftime(DATETIME_FORMAT), 'inline': True})
        fields.append({'name': "Docking", 'value': self.human_format_dockingaccess(), 'inline': True})
        fields.append({'name': "Notorious Access", 'value': self.human_format_notorious(), 'inline': True})

        self.bgstally.discord.post_embed(title, "A carrier jump has been scheduled", fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    def jump_cancelled(self):
        """
        The user cancelled their carrier jump
        """
        title:str = f"Jump Cancelled for Carrier {self.name}"

        fields = []
        fields.append({'name': "Current System", 'value': self.data.get('currentStarSystem', "Unknown"), 'inline': True})
        fields.append({'name': "Docking", 'value': self.human_format_dockingaccess(), 'inline': True})
        fields.append({'name': "Notorious Access", 'value': self.human_format_notorious(), 'inline': True})

        self.bgstally.discord.post_embed(title, "The scheduled carrier jump was cancelled", fields, None, DiscordChannel.FLEETCARRIER_OPERATIONS, None)


    def get_materials_plaintext(self, category: MaterialsCategory = None):
        """
        Return a list of formatted materials for posting to Discord
        """
        result:str = ""
        materials, key = self._get_materials(category)

        if materials is None: return ""

        for material in materials:
            if material[key] > 0: result += f"{material['locName']} x {material[key]} @ {self._human_format_price(material['price'])}\n"

        return result


    def get_materials_discord(self, category: MaterialsCategory = None) -> str:
        """
        Return a list of formatted materials for posting to Discord
        """
        result:str = ""
        materials, key = self._get_materials(category)

        if materials is None: return ""

        for material in materials:
            if material[key] > 0: result += f"{cyan(material['locName'])} x {green(material[key])} @ {red(self._human_format_price(material['price']))}\n"

        return result


    def human_format_dockingaccess(self) -> str:
        """
        Get the docking access in human-readable format
        """
        match (self.data.get('dockingAccess')):
            case "all": return "All"
            case "squadronfriends": return "Squadron and Friends"
            case "friends": return "Friends"
            case _: return "None"


    def human_format_notorious(self) -> str:
        """
        Get the notorious access in human-readable format
        """
        return 'Yes' if self.data.get('notoriousAccess', False) else 'No'


    def _human_format_price(self, num) -> str:
        """
        Format a BGS value into shortened human-readable text
        """
        num = float('{:.3g}'.format(num))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


    def _get_materials(self, category: MaterialsCategory = None) -> tuple[list|None, str|None]:
        """
        Return the materials list and price key for the specified category
        """
        if category == MaterialsCategory.SELLING:
            return self.onfoot_mats_selling, 'stock'
        elif category == MaterialsCategory.BUYING:
            return self.onfoot_mats_buying, 'outstanding'
        else:
            return None, None


    def _as_dict(self):
        """
        Return a Dictionary representation of our data, suitable for serializing
        """
        return {
            'name': self.name,
            'callsign': self.callsign,
            'onfoot_mats_selling': self.onfoot_mats_selling,
            'onfoot_mats_buying': self.onfoot_mats_buying,
            'data': self.data}


    def _from_dict(self, dict: dict):
        """
        Populate our data from a Dictionary that has been deserialized
        """
        self.name = dict.get('name')
        self.callsign = dict.get('callsign')
        self.onfoot_mats_selling = dict.get('onfoot_mats_selling')
        self.onfoot_mats_buying = dict.get('onfoot_mats_buying')
        self.data = dict.get('data')
