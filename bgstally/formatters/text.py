from bgstally.constants import DiscordPostStyle
from bgstally.debug import Debug
from bgstally.formatters.default import DefaultActivityFormatter
from bgstally.utils import _
from thirdparty.colors import *


class TextOnlyActivityFormatter(DefaultActivityFormatter):
    """The legacy output formatter. Uses the DefaulFormatter to create coloured text using ANSI formatting and
    UTF8 emojis to represent activity, but send as text only
    """

    def __init__(self, bgstally):
        """Instantiate class

        Args:
            bgstally (BGSTally): The BGSTally object
        """
        super().__init__(bgstally)


    def get_name(self) -> str:
        """Get the name of this formatter for presenting in the UI

        Returns:
            str: The name
        """
        return _("Text Only") # LANG: Name of default output formatter


    def get_mode(self) -> DiscordPostStyle:
        """Get the output format mode that this Formatter supports.

        Returns:
            DiscordPostStyle: The supported format mode
        """
        # Override text mode for this legacy formatter as the specific purpose of this formatter is
        # to force Discord posts to the old text-only format
        return DiscordPostStyle.TEXT


    # get_text() simply uses the superclass
