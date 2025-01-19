import hashlib
from datetime import UTC, datetime, timedelta
from json import JSONDecodeError

import plug
import requests
from requests import Response

from bgstally.constants import (DATETIME_FORMAT_ACTIVITY, DATETIME_FORMAT_DISPLAY, DATETIME_FORMAT_TICK_DETECTOR_GALAXY, DATETIME_FORMAT_TICK_DETECTOR_SYSTEM,
                                RequestMethod)
from bgstally.debug import Debug
from bgstally.requestmanager import BGSTallyRequest
from bgstally.utils import _
from config import config

TICKID_UNKNOWN = "unknown_tickid"
URL_GALAXY_TICK_DETECTOR = "http://tick.infomancer.uk/galtick.json"
URL_SYSTEM_TICK_DETECTOR = "http://tickapi.infomancer.uk/system/tick_by_addr"

class Tick:
    """
    Information about a tick
    """

    def __init__(self, bgstally, load: bool = False):
        self.bgstally = bgstally
        self.tick_id: str = TICKID_UNKNOWN
        self.tick_time: datetime = (datetime.now(UTC) - timedelta(days = 30)) # Default to a tick a month old
        if load: self.load()


    def fetch_tick(self):
        """
        Tick check and counter reset
        """
        try:
            response = requests.get(URL_GALAXY_TICK_DETECTOR, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            Debug.logger.error(f"Unable to fetch latest tick from {URL_GALAXY_TICK_DETECTOR}: {str(e)}")
            plug.show_error(_("{plugin_name} WARNING: Unable to fetch latest tick").format(plugin_name=self.bgstally.plugin_name)) # LANG: Main window error message
            return None
        else:
            tick_data: dict[str, str] = response.json()
            tick_time_raw: str|None = tick_data.get('lastGalaxyTick')

            if tick_time_raw is None:
                Debug.logger.error(f"Invalid tick data from {URL_GALAXY_TICK_DETECTOR}: {tick_data}")
                plug.show_error(_("{plugin_name} WARNING: Unable to fetch latest tick").format(plugin_name=self.bgstally.plugin_name)) # LANG: Main window error message
                return None

            tick_time: datetime = datetime.strptime(tick_time_raw, DATETIME_FORMAT_TICK_DETECTOR_GALAXY)
            tick_time = tick_time.replace(tzinfo=UTC)

            if tick_time > self.tick_time:
                # There is a newer tick
                self.tick_time = tick_time
                h = hashlib.shake_128(self.get_formatted().encode("utf-8"), usedforsecurity=False)
                self.tick_id = f"zoy-{h.hexdigest(10)}"

                return True

        return False


    def fetch_system_tick(self, system_address: str):
        """
        Tick check and counter reset
        """
        params: dict[str, str] = {'sysAddr': system_address}
        data: dict[str, str] = {'SystemAddress': system_address}

        self.bgstally.request_manager.queue_request(URL_SYSTEM_TICK_DETECTOR, RequestMethod.POST, params=params, data=data, callback=self._system_tick_received)


    def _system_tick_received(self, success: bool, response: Response, request: BGSTallyRequest):
        """
        Callback for system tick request
        """
        from bgstally.activity import Activity

        if not success:
            Debug.logger.error(f"Unable to fetch system tick from {request.endpoint}: {response}")
            plug.show_error(_("{plugin_name} WARNING: Unable to fetch system tick").format(plugin_name=self.bgstally.plugin_name))
            return

        try:
            tick_data: dict[str, any] = response.json()
        except JSONDecodeError:
            Debug.logger.warning(f"System tick data is invalid (JSON parse)")
            return

        if not isinstance(tick_data, dict):
            Debug.logger.warning(f"System tick data is invalid (not a dict)")
            return

        tick_time_raw: str|None = tick_data.get('timestamp')

        if tick_time_raw is None:
            Debug.logger.warning(f"System tick data is invalid (no timestamp)")
            return

        tick_time: datetime = datetime.strptime(tick_time_raw, DATETIME_FORMAT_TICK_DETECTOR_SYSTEM)
        tick_time = tick_time.replace(tzinfo=UTC)
        system_address: str = request.data.get('SystemAddress')

        if system_address is None:
            Debug.logger.warning(f"No system address in system tick callback data")
            return

        if tick_time < self.tick_time:
            # The system tick we've just fetched is older than the current galaxy tick, which must mean it hasn't been updated yet. Trigger another fetch
            # after a period of time.
            Debug.logger.warning(f"System tick is older than the current galaxy tick - should trigger another deferred fetch")
            if self.bgstally.ui.frame:
                params: dict[str, str] = {'sysAddr': system_address}
                self.bgstally.ui.frame.after(5000, self.bgstally.request_manager.queue_request(URL_SYSTEM_TICK_DETECTOR, RequestMethod.POST, params=params, data=request.data, callback=self._system_tick_received))

        # Store the system tick in the system activity.
        current_activity: Activity = self.bgstally.activity_manager.get_current_activity()
        if current_activity is None: return

        system: dict[str, any] = current_activity.get_system_by_address(system_address)
        if system is None: return

        system['TickTime'] = tick_time.strftime(DATETIME_FORMAT_ACTIVITY)


    def force_tick(self):
        """
        Force a new tick, user-initiated
        """
        # Set the tick time to the current datetime and generate a new 24-digit tick id prefixed with "frc-" to signify a forced tick
        self.tick_time = datetime.now()
        h = hashlib.shake_128(self.get_formatted().encode("utf-8"), usedforsecurity=False)
        self.tick_id = f"frc-{h.hexdigest(10)}"


    def load(self):
        """
        Load tick status from config
        """
        self.tick_id = config.get_str("XLastTick")
        self.tick_time = datetime.strptime(config.get_str("XTickTime", default=self.tick_time.strftime(DATETIME_FORMAT_TICK_DETECTOR_GALAXY)), DATETIME_FORMAT_TICK_DETECTOR_GALAXY)
        self.tick_time = self.tick_time.replace(tzinfo=UTC)


    def save(self):
        """
        Save tick status to config
        """
        config.set('XLastTick', self.tick_id)
        config.set('XTickTime', self.tick_time.strftime(DATETIME_FORMAT_TICK_DETECTOR_GALAXY))


    def get_formatted(self, format: str = DATETIME_FORMAT_DISPLAY, tick_time: datetime|None = None) -> str:
        """Return a formatted tick date/time

        Args:
            format (str, optional): The datetime format to use. Defaults to DATETIME_FORMAT_DISPLAY.
            tick_time (datetime | None, optional): The datetime to format. Defaults to the datetime for this Tick object.

        Returns:
            str: A formatted date/time string
        """
        if tick_time is None:
            return self.tick_time.strftime(format)
        else:
            return tick_time.strftime(format)


    def get_next_formatted(self, format: str = DATETIME_FORMAT_DISPLAY) -> str:
        """
        Return next predicted tick formated date/time
        """
        return self.next_predicted().strftime(format)


    def next_predicted(self) -> datetime:
        """
        Return the next predicted tick time (currently just add 24h to the current tick time)
        """
        return self.tick_time + timedelta(hours = 24)
