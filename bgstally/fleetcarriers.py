import json
from glob import glob
from os import path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

from bgstally.constants import FOLDER_OTHER_DATA, FleetCarrierType
from bgstally.fleetcarrier import FleetCarrier
from bgstally.utils import catch_exceptions

class FleetCarriers:
    """ Tracks every FleetCarrier we know about: our personal carrier, plus any squadron carrier. """

    @catch_exceptions
    def __init__(self, bgstally: 'BGSTally') -> None:
        self.bgstally:BGSTally = bgstally
        self.personal:FleetCarrier = FleetCarrier(bgstally, 0, FleetCarrierType.PERSONAL)
        self.carriers:dict[int, FleetCarrier] = {} # Non-personal carriers (currently just squadron), by carrier_id

        # Load any previously-saved non-personal carriers (currently just squadron)
        pattern:str = path.join(bgstally.plugin_dir, FOLDER_OTHER_DATA, "carrier_*.json")
        for file in glob(pattern):
            carrier_id:int = int(path.splitext(path.basename(file))[0].removeprefix("carrier_"))
            with open(file) as json_file:
                carrier_type:FleetCarrierType = FleetCarrierType(json.load(json_file).get('carrier_type', FleetCarrierType.SQUADRON))
            self.carriers[carrier_id] = FleetCarrier(bgstally, carrier_id, carrier_type)


    @property
    def squadron(self) -> FleetCarrier|None:
        """ Our squadron's carrier, if we've seen one """
        return next((c for c in self.carriers.values() if c.carrier_type == FleetCarrierType.SQUADRON), None)


    def get(self, carrier_id:int, carrier_type:FleetCarrierType) -> FleetCarrier:
        """ Return the FleetCarrier for carrier_id, creating it necessary """
        if carrier_type == FleetCarrierType.PERSONAL: return self.personal
        if carrier_id not in self.carriers:
            self.carriers[carrier_id] = FleetCarrier(self.bgstally, carrier_id, carrier_type)
        return self.carriers[carrier_id]


    @catch_exceptions
    def save_all(self) -> None:
        """ Save our personal carrier and any other tracked carriers """
        self.personal.save()
        for carrier in self.carriers.values(): carrier.save()
