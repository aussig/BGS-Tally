from collections import defaultdict

class State():
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, state:dict = {}):
        self.state: dict = {
            'GameLanguage':       None,  # From `Fileheader
            'GameVersion':        None,  # From `Fileheader
            'GameBuild':          None,  # From `Fileheader
            'Captain':            None,  # On a crew
            'Cargo':              defaultdict(int),
            'Credits':            None,
            'FID':                None,  # Frontier Cmdr ID
            'Horizons':           None,  # Does this user have Horizons?
            'Odyssey':            False,  # Have we detected we're running under Odyssey?
            'Loan':               None,
            'Raw':                defaultdict(int),
            'Manufactured':       defaultdict(int),
            'Encoded':            defaultdict(int),
            'Engineers':          {},
            'Rank':               {},
            'Reputation':         {},
            'Statistics':         {},
            'Role':               None,  # Crew role - None, Idle, FireCon, FighterCon
            'Friends':            set(),  # Online friends
            'ShipID':             None,
            'ShipIdent':          None,
            'ShipName':           None,
            'ShipType':           None,
            'HullValue':          None,
            'ModulesValue':       None,
            'UnladenMass':        None,
            'CargoCapacity':      None,
            'MaxJumpRange':       None,
            'FuelCapacity':       None,
            'Rebuy':              None,
            'Modules':            None,
            'CargoJSON':          None,  # The raw data from the last time cargo.json was read
            'Route':              None,  # Last plotted route from Route.json file
            'IsDocked':           False,  # Whether we think cmdr is docked
            'OnFoot':             False,  # Whether we think you're on-foot
            'Component':          defaultdict(int),      # Odyssey Components in Ship Locker
            'Item':               defaultdict(int),      # Odyssey Items in Ship Locker
            'Consumable':         defaultdict(int),      # Odyssey Consumables in Ship Locker
            'Data':               defaultdict(int),      # Odyssey Data in Ship Locker
            'BackPack':     {                      # Odyssey BackPack contents
                'Component':      defaultdict(int),    # BackPack Components
                'Consumable':     defaultdict(int),    # BackPack Consumables
                'Item':           defaultdict(int),    # BackPack Items
                'Data':           defaultdict(int),  # Backpack Data
            },
            'BackpackJSON':       None,  # Raw JSON from `Backpack.json` file, if available
            'ShipLockerJSON':     None,  # Raw JSON from the `ShipLocker.json` file, if available
            'SuitCurrent':        None,
            'Suits':              {},
            'SuitLoadoutCurrent': None,
            'SuitLoadouts':       {},
            'Taxi':               None,  # True whenever we are _in_ a taxi. ie, this is reset on Disembark etc.
            'Dropship':           None,  # Best effort as to whether or not the above taxi is a dropship.
            'StarPos':            None,  # Best effort current system's galaxy position.
            'SystemAddress':      None,
            'SystemName':         None,
            'SystemPopulation':   None,
            'Body':               None,
            'BodyID':             None,
            'BodyType':           None,
            'StationName':        None,

            'NavRoute':           None,
            'Powerplay':      {
                'Power':          None,
                'Rank':           None,
                'Merits':         None,
                'Votes':          None,
                'TimePledged':    None,
            },
        }
        self.update(state)

    def update(self, state:dict = {}) -> None:
        for key, value in state.items():
            if key in self.state:
                self.state[key] = value

    def get(self) -> dict:
        return self.state
