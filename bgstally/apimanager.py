import json
from datetime import datetime
from os import path

from bgstally.activity import Activity
from bgstally.api import API
from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_DATA

FILENAME = "apis.json"


class APIManager:
    """
    Handles a list of API objects.
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.apis:list[API] = []
        self.api_updated:bool = False

        self.load()

        if len(self.apis) == 0:
            # TODO: For the moment, ensure one API is created. Will need to manage multiple in the UI, and likely
            # not create one by default.
            self.apis.append(API(self.bgstally))


    def load(self):
        """
        Load all APIs from disk
        """
        file:str = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        if path.exists(file):
            with open(file) as json_file:
                apis_json:list = json.load(json_file)

            for api_json in apis_json:
                self.apis.append(API(self.bgstally, api_json))


    def save(self):
        """
        Save all APIs to disk
        """
        apis_json:list = []

        for api in self.apis:
            apis_json.append(api.as_dict())

        file:str = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(apis_json, outfile)


    def send_activity(self, activity:Activity, cmdr:str):
        """
        Activity data has been updated. Send it to all APIs.
        """
        api_activity:dict = self._build_api_activity(activity, cmdr)
        for api in self.apis:
            api.send_activity(api_activity)


    def send_event(self, event:dict, activity:Activity, cmdr:str):
        """
        Event has been received. Add it to the events queue.
        """
        api_event:dict = self._build_api_event(event, activity, cmdr)
        for api in self.apis:
            api.send_event(api_event)


    def _build_api_activity(self, activity:Activity, cmdr:str):
        """
        Build an API-ready activity ready for sending. A dict matching the API spec is built from the Activity data.
        """
        api_activity:dict = {
            'cmdr': cmdr,
            'tickid': activity.tick_id,
            'timestamp': datetime.utcnow().strftime(DATETIME_FORMAT_JOURNAL),
            'systems': []
        }

        for system in activity.systems.values():
            api_system:dict = {
                'name': system.get('System', ""),
                'address': system.get('SystemAddress', ""),
                'factions': [],
                'twkills': {}
            }

            for faction in system.get('Factions', {}).values():
                api_faction:dict = {
                    'name': faction.get('Faction', ""),
                    'state': faction.get('FactionState', ""),
                    'stations': []
                }

                if faction.get('Bounties', "0") != "0": api_faction['bvs'] = faction['Bounties']
                if faction.get('CombatBonds', "0") != "0": api_faction['cbs'] = faction['CombatBonds']
                if faction.get('ExoData', "0") != "0": api_faction['exobiology'] = faction['ExoData']
                if faction.get('CartData', "0") != "0": api_faction['exploration'] = faction['CartData']
                if faction.get('Scenarios', "0") != "0": api_faction['scenarios'] = faction['Scenarios']
                if faction.get('MissionPoints', "0") != "0": api_faction['infprimary'] = faction['MissionPoints']
                if faction.get('MissionPointsSecondary', "0") != "0": api_faction['infsecondary'] = faction['MissionPointsSecondary']
                if faction.get('MissionFailed', "0") != "0": api_faction['missionfails'] = faction['MissionFailed']
                if faction.get('GroundMurdered', "0") != "0": api_faction['murdersground'] = faction['GroundMurdered']
                if faction.get('Murdered', "0") != "0": api_faction['murdersspace'] = faction['Murdered']
                if faction.get('BlackMarketProfit', "0") != "0": api_faction['tradebm'] = faction['BlackMarketProfit']

                if sum(int(d['value']) for d in faction['TradeBuy']) > 0:
                    api_faction['tradebuy'] = {
                        'low': {
                            'items': faction['TradeBuy'][2]['items'],
                            'value': faction['TradeBuy'][2]['value']
                        },
                        'high': {
                            'items': faction['TradeBuy'][1]['items'],
                            'value': faction['TradeBuy'][1]['value']
                        }
                    }

                if sum(int(d['value']) for d in faction['TradeSell']) > 0:
                    api_faction['tradesell'] = {
                        'zero': {
                            'items': faction['TradeSell'][0]['items'],
                            'value': faction['TradeSell'][0]['value'],
                            'profit': faction['TradeSell'][0]['profit']
                        },
                        'low': {
                            'items': faction['TradeSell'][2]['items'],
                            'value': faction['TradeSell'][2]['value'],
                            'profit': faction['TradeSell'][2]['profit']
                        },
                        'high': {
                            'items': faction['TradeSell'][3]['items'],
                            'value': faction['TradeSell'][3]['value'],
                            'profit': faction['TradeSell'][3]['profit']
                        }
                    }

                if faction.get('GroundCZ', {}) != {}:
                    api_faction['czground'] = {
                        'low': faction['GroundCZ'].get('l', 0),
                        'medium': faction['GroundCZ'].get('m', 0),
                        'high': faction['GroundCZ'].get('h', 0),
                        'settlements': []
                    }
                    if faction.get('GroundCZSettlements', {}) != {}:
                        for settlement_name, settlement_data in faction['GroundCZSettlements'].items():
                            api_settlement:dict = {
                                'name': settlement_name,
                                'type': settlement_data.get('type', ""),
                                'count': settlement_data.get('count', 0)
                            }
                            api_faction['czground']['settlements'].append(api_settlement)

                if faction.get('SpaceCZ', {}) != {}:
                    api_faction['czspace'] = {
                        'low': faction['SpaceCZ'].get('l', 0),
                        'medium': faction['SpaceCZ'].get('m', 0),
                        'high': faction['SpaceCZ'].get('h', 0)
                    }

                if faction.get('TWStations', {}) != {}:
                    for station in faction.get('TWStations', {}).values():
                        api_station:dict = {
                            'name': station.get('name', "")
                        }
                        if station.get('cargo', {}).get('count', 0) > 0:
                            api_station['twcargo'] = station['cargo'] # dict containing 'count' and 'sum'

                        if sum(int(d['count']) for d in station['escapepods'].values()) > 0:
                            api_station['twescapepods'] = {
                                'low': station['escapepods']['l'],    # dict containing 'count' and 'sum'
                                'medium': station['escapepods']['m'], # dict containing 'count' and 'sum'
                                'high': station['escapepods']['h']    # dict containing 'count' and 'sum'
                            }
                        if sum(int(d['count']) for d in station['massacre'].values()) > 0:
                            api_station['twmassacre'] = {
                                'basilisk': station['massacre']['b'], # dict containing 'count' and 'sum'
                                'cyclops': station['massacre']['c'],  # dict containing 'count' and 'sum'
                                'hydra': station['massacre']['h'],    # dict containing 'count' and 'sum'
                                'medusa': station['massacre']['m'],   # dict containing 'count' and 'sum'
                                'orthrus': station['massacre']['o'],  # dict containing 'count' and 'sum'
                                'scout': station['massacre']['s']     # dict containing 'count' and 'sum'
                            }
                        if sum(int(d['count']) for d in station['passengers'].values()) > 0:
                            api_station['twpassengers'] = {
                                'low': station['passengers']['l'],    # dict containing 'count' and 'sum'
                                'medium': station['passengers']['m'], # dict containing 'count' and 'sum'
                                'high': station['passengers']['h']    # dict containing 'count' and 'sum'
                            }

                    api_faction['stations'].append(api_station)

                api_system['factions'].append(api_faction)

            if sum(system.get('TWKills', {}).values()) > 0:
                api_system['twkills'] = {
                    'basilisk': system['TWKills']['b'],
                    'cyclops': system['TWKills']['c'],
                    'hydra': system['TWKills']['h'],
                    'medusa': system['TWKills']['m'],
                    'orthrus': system['TWKills']['o'],
                    'scout': system['TWKills']['s']
                }

            api_activity['systems'].append(api_system)

        return api_activity


    def _build_api_event(self, event:dict, activity:Activity, cmdr:str):
        """
        Build an API-ready event ready for sending. This just involves enhancing the event with some
        additional data
        """

        # BGS-Tally specific global enhancements
        event['cmdr'] = cmdr
        event['tickid'] = activity.tick_id

        # Other global enhancements
        if 'StarSystem' not in event: event['StarSystem'] = activity.systems.get(self.bgstally.state.current_system_id, "")
        if 'SystemAddress' not in event: event['SystemAddress'] = self.bgstally.state.current_system_id

        # Event-specific enhancements
        match event.get('event'):
            case 'MarketBuy':
                if self.bgstally.market.available(event['MarketID']):
                    market_data:dict = self.bgstally.market.get_commodity(event['Type'])
                    event['StockBracket'] = market_data.get('StockBracket', 0)

            case 'MarketSell':
                if self.bgstally.market.available(event['MarketID']):
                    market_data:dict = self.bgstally.market.get_commodity(event['Type'])
                    event['DemandBracket'] = market_data.get('DemandBracket', 0)

        return event
