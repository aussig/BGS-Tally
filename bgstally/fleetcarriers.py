import json
from glob import glob
from os import path, remove
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

from bgstally.constants import FOLDER_OTHER_DATA, FleetCarrierType
from bgstally.fleetcarrier import FleetCarrier
from bgstally.ravencolonial import Spansh
from bgstally.utils import catch_exceptions

class FleetCarriers:
    """ Tracks every FleetCarrier we know about: our personal carrier, our squadron's, and any
    third-party carrier we've visited and chosen to track. """

    @catch_exceptions
    def __init__(self, bgstally: 'BGSTally') -> None:
        self.bgstally:BGSTally = bgstally
        self.personal:FleetCarrier = FleetCarrier(bgstally, 0, FleetCarrierType.PERSONAL)
        self.carriers:dict[int, FleetCarrier] = {} # Non-personal carriers (squadron/third-party), by carrier_id

        # Load any previously-saved non-personal carriers (squadron/third-party)
        pattern:str = path.join(bgstally.plugin_dir, FOLDER_OTHER_DATA, "carrier_*.json")
        for file in glob(pattern):
            carrier_id:int = int(path.splitext(path.basename(file))[0].removeprefix("carrier_"))
            with open(file) as json_file:
                carrier_type:FleetCarrierType = FleetCarrierType(json.load(json_file).get('carrier_type', FleetCarrierType.SQUADRON))
            self.carriers[carrier_id] = FleetCarrier(bgstally, carrier_id, carrier_type)


    def by_type(self, carrier_type:FleetCarrierType) -> list[FleetCarrier]:
        """ Every non-personal carrier we know of, of a given type """
        return [c for c in self.carriers.values() if c.carrier_type == carrier_type]


    @property
    def squadron(self) -> FleetCarrier|None:
        """ Our squadron's carrier, if we've seen one """
        return next(iter(self.by_type(FleetCarrierType.SQUADRON)), None)


    @property
    def third_party(self) -> list[FleetCarrier]:
        """ Every third-party carrier we're currently tracking """
        return self.by_type(FleetCarrierType.THIRDPARTY)


    def get(self, carrier_id:int, carrier_type:FleetCarrierType) -> FleetCarrier:
        """ Return the FleetCarrier for carrier_id, creating it if necessary """
        if carrier_type == FleetCarrierType.PERSONAL: return self.personal
        if carrier_id not in self.carriers:
            self.carriers[carrier_id] = FleetCarrier(self.bgstally, carrier_id, carrier_type)
        return self.carriers[carrier_id]


    def find(self, carrier_id:int) -> FleetCarrier|None:
        """ Return an already-known carrier by id alone, without creating a new one """
        if carrier_id == self.personal.carrier_id: return self.personal
        return self.carriers.get(carrier_id)


    def remove(self, carrier_id:int) -> None:
        """ Stop tracking a third-party carrier and delete its local data """
        carrier:FleetCarrier|None = self.carriers.pop(carrier_id, None)
        if carrier is None: return
        file:str = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, carrier._get_filename())
        if path.exists(file): remove(file)


    @catch_exceptions
    def save_all(self) -> None:
        """ Save our personal carrier and any other tracked carriers """
        self.personal.save()
        for carrier in self.carriers.values(): carrier.save()


    def refresh_from_spansh(self) -> None:
        """ Refresh squadron/third-party carrier market data from Spansh """
        for carrier in self.carriers.values():
            Spansh().import_fleetcarrier(carrier)


    def track_by_callsign(self, callsign:str, callback:Callable[[], None]) -> None:
        """ Start tracking a third-party carrier """
        def _resolved(market_id:int|None) -> None:
            if market_id is not None:
                Spansh().import_fleetcarrier(self.get(market_id, FleetCarrierType.THIRDPARTY))
            callback()
        Spansh().find_carrier(callsign, _resolved)
