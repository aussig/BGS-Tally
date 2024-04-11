from bgstally.constants import FormatMode
from bgstally.debug import Debug
from bgstally.formatters.default import DefaultFormatter
from bgstally.state import State
from bgstally.utils import _
from thirdparty.colors import *


class LegacyFormatter(DefaultFormatter):
    """The default output formatter. Produces coloured text using ANSI formatting and UTF8 emojis
    to represent activity when sending to Discord, and equivalent string representations when not
    """

    def __init__(self, state: State):
        """Instantiate class

        Args:
            state (State): The State object containing persistent values and settings
        """
        super(LegacyFormatter, self).__init__(state)


    def get_name(self) -> str:
        """Get the name of this formatter for presenting in the UI

        Returns:
            str: The name
        """
        return _("Legacy") # LANG: Name of default output formatter


    def get_mode(self) -> FormatMode:
        """Get the output format mode that this Formatter supports

        Returns:
            FormatMode: The supported format mode
        """
        return FormatMode.TEXT
