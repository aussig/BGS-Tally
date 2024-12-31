import json
from datetime import datetime, UTC
from os import path
from enum import Enum

from bgstally.activity import Activity
from bgstally.api import API
from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_OTHER_DATA
from bgstally.debug import Debug
from bgstally.utils import get_by_path

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
        file:str = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    apis_json:list = json.load(json_file)

                for api_json in apis_json:
                    self.apis.append(API(self.bgstally, api_json))
            except Exception as e:
                Debug.logger.info(f"Unable to load {file}")


    def save(self):
        """
        Save all APIs to disk
        """
        apis_json:list = []

        for api in self.apis:
            apis_json.append(api.as_dict())

        file:str = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(apis_json, outfile)


    def send_activity(self, activity:Activity, cmdr:str):
        """
        Activity data has been updated. Send it to all APIs.
        """
        api_activity:dict = self._build_api_activity(activity, cmdr)
        for api in self.apis:
            api.send_activity(api_activity)


    def send_event(self, event: dict, activity: Activity, cmdr: str, mission: dict = {}):
        """Event has been received. Add it to the events queue.

        Args:
            event (dict): A dict containing all the event fields
            activity (Activity): The activity object
            cmdr (str): The CMDR name
            mission (dict, optional): Information about the mission, if applicable. Defaults to {}.
        """
        api_event: dict = self._build_api_event(event, activity, cmdr, mission)
        for api in self.apis:
            api.send_event(api_event)


    def _build_api_activity(self, activity:Activity, cmdr:str):
        """
        Build an API-ready activity ready for sending. A dict matching the API spec is built from the Activity data.
        """
        api_activity:dict = {
            'cmdr': cmdr,
            'tickid': activity.tick_id,
            'ticktime': activity.tick_time.strftime(DATETIME_FORMAT_JOURNAL),
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
                inf_primary:int = sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction['MissionPoints'].items())
                inf_secondary:int = sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction['MissionPointsSecondary'].items())
                if inf_primary != 0: api_faction['infprimary'] = str(inf_primary)
                if inf_secondary != 0: api_faction['infsecondary'] = str(inf_secondary)
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
                            'items': faction['TradeBuy'][3]['items'],
                            'value': faction['TradeBuy'][3]['value']
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

                if sum(faction.get('SandR', {}).values()) > 0:
                    api_faction['sandr'] = {
                        'damagedpods': get_by_path(faction, ['SandR', 'dp'], 0),
                        'occupiedpods': get_by_path(faction, ['SandR', 'op'], 0),
                        'thargoidpods': get_by_path(faction, ['SandR', 'tp'], 0),
                        'blackboxes': get_by_path(faction, ['SandR', 'bb'], 0),
                        'wreckagecomponents': get_by_path(faction, ['SandR', 'wc'], 0),
                        'personaleffects': get_by_path(faction, ['SandR', 'pe'], 0),
                        'politicalprisoners': get_by_path(faction, ['SandR', 'pp'], 0),
                        'hostages': get_by_path(faction, ['SandR', 'h'], 0)
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
                        # TW settlement reactivation missions
                        if station.get('reactivate', 0) > 0:
                            api_station['twreactivate'] = station['reactivate'] # int

                    api_faction['stations'].append(api_station)

                api_system['factions'].append(api_faction)

            if sum(system.get('TWKills', {}).values()) > 0:
                api_system['twkills'] = {
                    'banshee': system['TWKills'].get('ba', 0),
                    'basilisk': system['TWKills'].get('b', 0),
                    'cyclops': system['TWKills'].get('c', 0),
                    'hydra': system['TWKills'].get('h', 0),
                    'medusa': system['TWKills'].get('m', 0),
                    'orthrus': system['TWKills'].get('o', 0),
                    'revenant': system['TWKills'].get('r', 0),
                    'scout': system['TWKills'].get('s', 0),
                    'scythe-glaive': system['TWKills'].get('sg', 0)
                }

            if sum(int(d['delivered']) for d in system.get('TWSandR', {}).values()) > 0:
                api_system['twsandr'] = {
                    'damagedpods': system['TWSandR']['dp']['delivered'],
                    'occupiedpods': system['TWSandR']['op']['delivered'],
                    'thargoidpods': system['TWSandR']['tp']['delivered'],
                    'blackboxes': system['TWSandR']['bb']['delivered'],
                    'tissuesamples': system['TWSandR']['t']['delivered']
                }

            # TW Reactivated settlements in system
            if system.get('TWReactivate', 0) > 0:
                api_system['twreactivate'] = system.get('TWReactivate', 0)

            api_activity['systems'].append(api_system)

        return api_activity


    def _build_api_event(self, event:dict, activity:Activity, cmdr:str, mission:dict = {}):
        """
        Build an API-ready event ready for sending. This just involves enhancing the event with some
        additional data
        """

        # Remove all '_Localised' event parameters
        event = self._filter_localised(event)

        # BGS-Tally specific global enhancements
        event['cmdr'] = cmdr
        event['tickid'] = activity.tick_id
        event['ticktime'] = activity.tick_time.strftime(DATETIME_FORMAT_JOURNAL)

        # Other global enhancements
        if 'StationFaction' not in event: event['StationFaction'] = {'Name': self.bgstally.state.station_faction}
        if 'StarSystem' not in event: event['StarSystem'] = get_by_path(activity.systems, [self.bgstally.state.current_system_id, 'System'], "")
        if 'SystemAddress' not in event: event['SystemAddress'] = self.bgstally.state.current_system_id
        if 'timestamp' not in event: event['timestamp'] = datetime.now(UTC).strftime(DATETIME_FORMAT_JOURNAL),

        # Event-specific enhancements
        match event.get('event'):
            case 'MarketBuy':
                if self.bgstally.market.available(event['MarketID']):
                    market_data:dict = self.bgstally.market.get_commodity(event['Type'])
                    event['StockBracket'] = market_data.get('StockBracket', 0)
                    event['Stock'] = market_data.get('Stock', 0)

            case 'MarketSell':
                if self.bgstally.market.available(event['MarketID']):
                    market_data:dict = self.bgstally.market.get_commodity(event['Type'])
                    event['DemandBracket'] = market_data.get('DemandBracket', 0)
                    event['Demand'] = market_data.get('Demand', 0)

            case 'MissionFailed' | 'MissionAbandoned':
                event['StationFaction'] = {'Name': mission.get('Faction', "")}

        return event


    def _filter_localised(self, d: dict[str, any]) -> dict[str, any]:
        """
        Recursively remove any dict keys with names ending `_Localised` from a dict.

        :param d: dict to filter keys of.
        :return: The filtered dict.
        """
        filtered: dict[str, any] = dict()
        for k, v in d.items():
            if k.endswith('_Localised'):
                pass

            elif hasattr(v, 'items'):  # dict -> recurse
                filtered[k] = self._filter_localised(v)

            elif isinstance(v, list):  # list of dicts -> recurse
                filtered[k] = [self._filter_localised(x) if hasattr(x, 'items') else x for x in v]

            else:
                filtered[k] = v

        return filtered
