import configparser as cp
import os.path
from bgstally.debug import Debug

FOLDERNAME = "config"
MAIN_FILENAME = "config.ini"
USER_FILENAME = "userconfig.ini"


class Config(object):
    """
    Manages the plugin config files
    """
    def __init__(self, bgstally):
        self.config: cp.ConfigParser = cp.ConfigParser()

        main_filepath: str = os.path.join(bgstally.plugin_dir, FOLDERNAME, MAIN_FILENAME)
        if os.path.exists(main_filepath):
            try:
                self.config.read(main_filepath)
            except Exception as e:
                Debug.logger.error(f"Unable to load main config file {main_filepath}")

        # If a user config file exists then it overrides the main config file
        user_filepath: str = os.path.join(bgstally.plugin_dir, FOLDERNAME, USER_FILENAME)
        if os.path.exists(user_filepath):
            try:
                self.config.read(user_filepath)
            except Exception as e:
                Debug.logger.info(f"No user defined config file found {user_filepath}")


    def apikey_inara(self) -> str | None:
        """Get the Inara API key from config

        Returns:
            str | None: The Inara API key
        """
        return self.config.get('apikeys', 'inara')


    def apikey_sentry(self) -> str | None:
        """Get the Sentry API key from config

        Returns:
            str | None: The Sentry API key
        """
        return self.config.get('apikeys', 'sentry')


    def api(self, name: str) -> dict | None:
        """Fetch all information about a given API

        Args:
            name (str): The API name, which maps to a config section with the name prefixed by 'apis.'

        Returns:
            dict | None: The configuration for the given API
        """
        result: dict | None = None

        try:
            result = self.config[f'apis.{name}']
        except KeyError as e:
            Debug.logger.error(f"Tried to access API config from '{name}' which doesn't exist", exc_info=e)

        return result


    def overlay(self) -> dict | None:
        """Fetch all information about the overlay configuration

        Returns:
            dict: The overlay configuration
        """
        result: dict | None = None

        try:
            result = self.config['overlay']
        except KeyError as e:
            Debug.logger.error(f"Tried to access overlay config which doesn't exist", exc_info=e)

        return result


    def overlay_frame(self, name: str) -> dict | None:
        """Fetch all information about a given overlay panel

        Args:
            name (str): The overlay panel name, which maps to a config section with the name prefixed by 'overlay.frame.'

        Returns:
            dict | None: The configuration for the given panel
        """
        result: dict | None = None

        try:
            result = self.config[f'overlay.frame.{name}']
        except KeyError as e:
            Debug.logger.error(f"Tried to access overlay frame config from '{name}' which doesn't exist", exc_info=e)

        return result
