from copy import deepcopy
from os import listdir, mkdir, path

from config import config

from bgstally.activity import Activity
from bgstally.debug import Debug
from bgstally.tick import Tick

FILE_LEGACY_CURRENTDATA = "Today Data.txt"
FILE_LEGACY_PREVIOUSDATA = "Yesterday Data.txt"
FOLDER_ACTIVITYDATA = "activitydata"
FILE_SUFFIX = ".json"


class ActivityManager:
    """
    Handles a list of Activity objects, each representing the data for a tick, handles updating activity, and manages
    the data storage of Activity logs.
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.activity_data = []
        self.current_activity = None

        self._load()

        if self.activity_data == [] or self.current_activity == None:
            # Either no activity data, or the activity data file for the last stored tick has been manually deleted
            self.current_activity = Activity(self.bgstally, self.bgstally.tick)
            self.activity_data.append(self.current_activity)
            self.activity_data.sort(reverse=True)


    def save(self):
        """
        Save all activity data
        """
        for activity in self.activity_data:
            activity.save(path.join(self.bgstally.plugin_dir, FOLDER_ACTIVITYDATA, activity.tick_id + FILE_SUFFIX))


    def get_current_activity(self):
        """
        Get the latest Activity, i.e. current tick
        """
        return self.current_activity


    def get_previous_activities(self):
        """
        Get a list of previous Activities.
        """
        return self.activity_data[1:]


    def new_tick(self, tick: Tick):
        """
        New tick detected, duplicate the current Activity object
        """
        # Note Activity uses a customised __deepcopy__ that only deep copies data, not class instances.
        new_activity = deepcopy(self.current_activity)
        new_activity.tick_id = tick.tick_id
        new_activity.tick_time = tick.tick_time
        new_activity.discord_bgs_messageid = None
        new_activity.discord_tw_messageid = None
        new_activity.clear_activity(self.bgstally.mission_log)
        self.activity_data.append(new_activity)
        self.activity_data.sort(reverse=True)
        self.current_activity = new_activity


    def _load(self):
        """
        Load all activity data
        """
        # Handle modern data from subfolder
        filepath = path.join(self.bgstally.plugin_dir, FOLDER_ACTIVITYDATA)
        if not path.exists(filepath): mkdir(filepath)
        for activityfilename in listdir(filepath):
            if activityfilename.endswith(FILE_SUFFIX):
                activity = Activity(self.bgstally, Tick(self.bgstally))
                activity.load(path.join(filepath, activityfilename))
                self.activity_data.append(activity)
                if activity.tick_id == self.bgstally.tick.tick_id: self.current_activity = activity

        # Handle legacy data if it exists - parse and migrate to new format
        filepath = path.join(self.bgstally.plugin_dir, FILE_LEGACY_PREVIOUSDATA)
        if path.exists(filepath): self._convert_legacy_data(filepath, Tick(self.bgstally), config.get_str('XDiscordPreviousMessageID')) # Fake a tick for previous legacy - we don't have tick_id or tick_time
        filepath = path.join(self.bgstally.plugin_dir, FILE_LEGACY_CURRENTDATA)
        if path.exists(filepath): self._convert_legacy_data(filepath, self.bgstally.tick, config.get_str('XDiscordCurrentMessageID'))

        self.activity_data.sort(reverse=True)


    def _convert_legacy_data(self, filepath: str, tick: Tick, discord_bgs_messageid: str):
        """
        Convert a legacy activity data file to new location and format.
        """
        for activity in self.activity_data:
            if activity.tick_id == tick.tick_id:
                # We already have modern data for this legacy tick ID, ignore it and delete the file
                Debug.logger.warning(f"Tick data already exists for tick {tick.tick_id} when loading legacy data. Ignoring legacy data.")
                # TODO: remove(filepath) - Can be done in a future version of the plugin, when we are sure everything is solid
                return

        activity = Activity(self.bgstally, tick, discord_bgs_messageid)
        activity.load_legacy_data(filepath)
        self.activity_data.append(activity)
        if activity.tick_id == tick.tick_id: self.current_activity = activity
