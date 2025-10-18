import logging
from os import path

from config import appname # type: ignore


class Debug:
    logger: logging.Logger

    def __init__(self, bgstally, dev_mode: bool = False) -> None:
        # A Logger is used per 'found' plugin to make it easy to include the plugin's
        # folder name in the logging output format.
        # NB: plugin_name here *must* be the plugin's folder name as per the preceding
        #     code, else the logger won't be properly set up.
        Debug.logger = logging.getLogger(f'{appname}.{path.basename(bgstally.plugin_dir)}')

        if dev_mode == False:
            Debug.logger.setLevel(logging.INFO)
        else:
            Debug.logger.setLevel(logging.DEBUG)
