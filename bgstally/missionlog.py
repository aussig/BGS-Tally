import json
from datetime import UTC, datetime, timedelta
from os import path, remove

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_OTHER_DATA
from bgstally.debug import Debug

FILENAME = "missionlog.json"
FILENAME_LEGACY = "MissionLog.txt"
TIME_MISSION_EXPIRY_D = 7


class MissionLog:
    """
    Handle a log of all in-progress missions
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.missionlog = []
        self.load()
        self._expire_old_missions()


    def load(self):
        """
        Load state from file
        """
        # New location
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    self.missionlog = json.load(json_file)
                    return
            except Exception as e:
                Debug.logger.info(f"Unable to load {file}")

        # Legacy location
        file = path.join(self.bgstally.plugin_dir, FILENAME_LEGACY)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    self.missionlog = json.load(json_file)
                remove(file)
            except Exception as e:
                Debug.logger.info(f"Unable to load and remove {file}")


    def save(self):
        """
        Save state to file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self.missionlog, outfile)


    def get_missionlog(self):
        """
        Get the current missionlog
        """
        return self.missionlog


    def get_mission(self, missionid: int):
        """
        Fetch a given mission from the missionlog, or None if not found
        """
        if missionid is None: return None

        for mission in self.missionlog:
            if mission['MissionID'] == missionid: return mission
        return None


    def add_mission(self, name: str, faction: str, missionid: str, expiry: str,
                    destination_system: str, destination_settlement: str, system_name: str, station_name: str,
                    commodity_count: int, passenger_count: int, kill_count: int,
                    target_faction: str):
        """
        Add a mission to the missionlog
        """
        self.missionlog.append({'Name': name, 'Faction': faction, 'MissionID': missionid, 'Expiry': expiry,
                                'DestinationSystem': destination_system, 'DestinationSettlement': destination_settlement, 'System': system_name, 'Station': station_name,
                                'CommodityCount': commodity_count, 'PassengerCount': passenger_count, 'KillCount': kill_count,
                                'TargetFaction': target_faction})


    def delete_mission_by_id(self, missionid: str):
        """
        Delete the mission with the given id from the missionlog
        """
        for i in range(len(self.missionlog)):
            if self.missionlog[i]['MissionID'] == missionid:
                self.missionlog.pop(i)
                break


    def delete_mission_by_index(self, missionindex: int):
        """
        Delete the mission at the given index from the missionlog
        """
        self.missionlog.pop(missionindex)


    def get_active_systems(self):
        """
        Return a list of systems that have currently active missions
        """
        systems = [x['System'] for x in self.missionlog]
        # De-dupe before returning
        return list(dict.fromkeys(systems))


    def _expire_old_missions(self):
        """
        Clear out all missions older than 7 days from the mission log
        """
        for mission in reversed(self.missionlog):
            # Old missions pre v1.11.0 and missions with missing expiry dates don't have Expiry stored. Set to 7 days ahead for safety
            if not 'Expiry' in mission or mission['Expiry'] == "": mission['Expiry'] = (datetime.now(UTC) + timedelta(days = TIME_MISSION_EXPIRY_D)).strftime(DATETIME_FORMAT_JOURNAL)

            # Need to do this shenanegans to parse a tz-aware timestamp from a string
            expiry_timestamp: datetime = datetime.strptime(mission['Expiry'], DATETIME_FORMAT_JOURNAL)
            expiry_timestamp = expiry_timestamp.replace(tzinfo=UTC)

            timedifference = datetime.now(UTC) - expiry_timestamp
            if timedifference > timedelta(days = TIME_MISSION_EXPIRY_D):
                # Keep missions for a while after they have expired, so we can log failed missions correctly
                self.missionlog.remove(mission)
