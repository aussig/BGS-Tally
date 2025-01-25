from copy import deepcopy
from datetime import datetime, timedelta
from os import listdir, mkdir, path, remove, rename

from bgstally.activity import Activity
from bgstally.constants import FILE_SUFFIX
from bgstally.debug import Debug
from bgstally.tick import Tick

FILE_LEGACY_CURRENTDATA = "Today Data.txt"
FILE_LEGACY_PREVIOUSDATA = "Yesterday Data.txt"
FOLDER_ACTIVITYDATA = "activitydata"
FOLDER_ACTIVITYDATA_ARCHIVE = "archive"
KEEP_CURRENT_ACTIVITIES = 20


class ActivityManager:
    """
    Handles a list of Activity objects, each representing the data for a tick, handles updating activity, and manages
    the data storage of Activity logs.
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.activity_data: list[Activity] = []
        self.current_activity: Activity|None = None

        self._load()
        self._archive_old_activity()

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
            if activity.tick_id is None: continue
            activity.save(path.join(self.bgstally.plugin_dir, FOLDER_ACTIVITYDATA, activity.get_filename()))


    def get_current_activity(self) -> Activity|None:
        """
        Get the latest Activity, i.e. current tick
        """
        return self.current_activity


    def get_previous_activities(self) -> list[Activity]:
        """
        Get a list of previous Activities.
        """
        return self.activity_data[1:]


    def query_activity(self, start_date: datetime) -> Activity:
        """Aggregate all activity back to and including the tick encompassing a given start date

        Args:
            start_date (datetime): The start date

        Returns:
            Activity: A new Activity object containing the aggregated data.
        """
        result: Activity = Activity(self.bgstally)

        # Iterate activities (already kept sorted by date, newest first)
        for activity in self.activity_data:

            result = result + activity

            if activity.tick_time <= start_date:
                # Once we reach an activity that is older than our start date, stop. Note that we have INCLUDED the
                # activity which overlaps with the start_date
                break

        return result



    def new_tick(self, tick: Tick, forced: bool) -> bool:
        """
        New tick detected, duplicate the current Activity object or ignore if it's older than current tick.
        """

        if tick.tick_time < self.current_activity.tick_time:
            # An inbound tick is older than the current tick. The only valid situation for this is if the user has done a Force Tick
            # but a new tick was then detected with an earlier timestamp. Ignore the tick in this situation.
            return False
        else:
            # An inbound tick is newer than the current tick. Create a new Activity object.
            # Note Activity uses a customised __deepcopy__ that only deep copies data, not class instances.
            new_activity:Activity = deepcopy(self.current_activity)
            new_activity.tick_id = tick.tick_id
            new_activity.tick_time = tick.tick_time
            new_activity.tick_forced = forced
            new_activity.discord_webhook_data = {}
            new_activity.discord_notes = ""
            new_activity.clear_activity(self.bgstally.mission_log)
            self.activity_data.append(new_activity)
            self.activity_data.sort(reverse=True)
            self.current_activity = new_activity

            return True


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
        if path.exists(filepath): self._convert_legacy_data(filepath, Tick(self.bgstally)) # Fake a tick for previous legacy - we don't have tick_id or tick_time
        filepath = path.join(self.bgstally.plugin_dir, FILE_LEGACY_CURRENTDATA)
        if path.exists(filepath): self._convert_legacy_data(filepath, self.bgstally.tick)

        self.activity_data.sort(reverse=True)


    def _convert_legacy_data(self, filepath: str, tick: Tick):
        """
        Convert a legacy activity data file to new location and format.
        """
        for activity in self.activity_data:
            if activity.tick_id == tick.tick_id:
                # We already have modern data for this legacy tick ID, ignore it and delete the file
                Debug.logger.info(f"Tick data already exists for tick {tick.tick_id} when loading legacy data. Deleting legacy data.")
                remove(filepath)
                return

        activity = Activity(self.bgstally, tick)
        activity.load_legacy_data(filepath)
        activity.save(path.join(self.bgstally.plugin_dir, FOLDER_ACTIVITYDATA, activity.get_filename()))
        self.activity_data.append(activity)
        if activity.tick_id == tick.tick_id: self.current_activity = activity


    def _archive_old_activity(self):
        """
        Move all old activity reports to an archive folder
        """
        archive_filepath = path.join(self.bgstally.plugin_dir, FOLDER_ACTIVITYDATA, FOLDER_ACTIVITYDATA_ARCHIVE)
        if not path.exists(archive_filepath): mkdir(archive_filepath)

        # Split list, keep first KEEP_CURRENT_ACTIVITIES in
        activity_to_archive: list[Activity] = self.activity_data[KEEP_CURRENT_ACTIVITIES:]
        self.activity_data = self.activity_data[:KEEP_CURRENT_ACTIVITIES]

        for activity in activity_to_archive:
            try:
                Debug.logger.info(f"Archiving {activity.get_filename()}")
                rename(path.join(self.bgstally.plugin_dir, FOLDER_ACTIVITYDATA, activity.get_filename()),
                       path.join(self.bgstally.plugin_dir, archive_filepath, activity.get_filename()))
            except FileExistsError: # Destination exists
                Debug.logger.warning(f"Attempt to archive failed, destination file already exists")
                continue
            except FileNotFoundError: # Source doesn't exist
                Debug.logger.warning(f"Attempt to archive failed, source file doesn't exist")
                continue
