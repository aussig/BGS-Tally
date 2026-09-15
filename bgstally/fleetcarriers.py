from glob import glob
from os import path, remove
from threading import Thread
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

from bgstally.constants import FOLDER_CARRIERS, FOLDER_OTHER_DATA, FleetCarrierType
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

        # Load any previously-saved non-personal carriers (squadron/third-party), one file per callsign
        pattern:str = path.join(bgstally.plugin_dir, FOLDER_OTHER_DATA, FOLDER_CARRIERS, "*.json")
        for file in glob(pattern):
            callsign:str = path.splitext(path.basename(file))[0]
            fc:FleetCarrier = FleetCarrier(bgstally, 0, FleetCarrierType.THIRDPARTY, callsign) # load() fills in the real id/type
            self.carriers[fc.carrier_id] = fc


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


    def add(self, carrier_id:int, type:FleetCarrierType, station:str|None = None, system:str|None = None) -> None:
        """ Add a new carrier """
        if not carrier_id or carrier_id in self.carriers: return
        self.carriers[carrier_id] = FleetCarrier(self.bgstally, carrier_id, type, station)
        if system: self.carriers[carrier_id].overview['currentStarSystem'] = system

    def get(self, carrier_id:int, carrier_type:FleetCarrierType, callsign:str|None = None) -> FleetCarrier:
        """ Return the FleetCarrier for carrier_id, creating it if necessary """
        if carrier_type == FleetCarrierType.PERSONAL: return self.personal
        if carrier_id not in self.carriers:
            self.carriers[carrier_id] = FleetCarrier(self.bgstally, carrier_id, carrier_type, callsign)
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


    def refresh_markets(self) -> None:
        """ Refresh each carrier's cargo data, one thread per carrier """

        # Personal needs special treatment
        #Spansh().import_fleetcarrier(self.personal)
        for carrier in self.carriers.values():
            Thread(target=carrier.update_carrier, daemon=True, name=f"FC update {carrier.carrier_id}").start()


    def track_by_callsign(self, callsign:str) -> bool:
        """ Start tracking a third-party carrier """
        market_id:int|None = Spansh().find_carrier(callsign)
        if market_id is None: return False

        fc:FleetCarrier = self.get(market_id, FleetCarrierType.THIRDPARTY, callsign)
        Spansh().import_fleetcarrier(fc)

        return True