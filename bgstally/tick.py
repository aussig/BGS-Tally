import hashlib
from datetime import UTC, datetime, timedelta

import plug
import requests

from bgstally.debug import Debug
from bgstally.utils import _
from config import config

DATETIME_FORMAT_TICK_DETECTOR = "%Y-%m-%dT%H:%M:%S.%fZ"
DATETIME_FORMAT_DISPLAY = "%Y-%m-%d %H:%M:%S"
TICKID_UNKNOWN = "unknown_tickid"
URL_TICK_DETECTOR = "http://tick.infomancer.uk/galtick.json"


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
            response = requests.get(URL_TICK_DETECTOR, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            Debug.logger.error(f"Unable to fetch latest tick from {URL_TICK_DETECTOR}: {str(e)}")
            plug.show_error(_("{plugin_name} WARNING: Unable to fetch latest tick").format(plugin_name=self.bgstally.plugin_name)) # LANG: Main window error message
            return None
        else:
            tick_data: dict[str, str] = response.json()
            tick_time_raw: str|None = tick_data.get('lastGalaxyTick')

            if tick_time_raw is None:
                Debug.logger.error(f"Invalid tick data from {URL_TICK_DETECTOR}: {tick_data}")
                plug.show_error(_("{plugin_name} WARNING: Unable to fetch latest tick").format(plugin_name=self.bgstally.plugin_name)) # LANG: Main window error message
                return None

            tick_time: datetime = datetime.strptime(tick_time_raw, DATETIME_FORMAT_TICK_DETECTOR)

            if tick_time > self.tick_time:
                # There is a newer tick
                self.tick_time = tick_time
                h = hashlib.shake_128(self.get_formatted().encode("utf-8"), usedforsecurity=False)
                self.tick_id = f"zoy-{h.hexdigest(10)}"

                return True

        return False


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
        self.tick_time = datetime.strptime(config.get_str("XTickTime", default=self.tick_time.strftime(DATETIME_FORMAT_TICK_DETECTOR)), DATETIME_FORMAT_TICK_DETECTOR)


    def save(self):
        """
        Save tick status to config
        """
        config.set('XLastTick', self.tick_id)
        config.set('XTickTime', self.tick_time.strftime(DATETIME_FORMAT_TICK_DETECTOR))


    def get_formatted(self, format: str = DATETIME_FORMAT_DISPLAY) -> str:
        """
        Return a formatted tick date/time
        """
        return self.tick_time.strftime(format)


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
