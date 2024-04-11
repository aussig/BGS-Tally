from bgstally.activity import Activity
from bgstally.constants import DiscordActivity, FormatMode
from bgstally.debug import Debug
from bgstally.formatters.base import FieldFormatterInterface
from bgstally.state import State
from bgstally.utils import _


class DummyFormatter(FieldFormatterInterface):
    """The interface for all discord formatters. Every formatter should implement this interface
    """

    def __init__(self, state: State):
        """Instantiate class

        Args:
            state (State): The State object containing persistent values and settings
        """
        super(DummyFormatter, self).__init__(state)


    def get_name(self) -> str:
        """Get the name of this formatter

        Returns:
            str: The name of this formatter for choosing in the UI
        """
        return _("Dummy")


    def get_mode(self) -> FormatMode:
        """Get the output format mode that this Formatter supports

        Returns:
            FormatMode: The supported format mode
        """
        return FormatMode.FIELDS


    def get_fields(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> list[dict]:
        """Generate a list of discord embed fields, conforming to the embed field spec defined here:
        https://birdie0.github.io/discord-webhooks-guide/structure/embed/fields.html - i.e. each field should be a dict
        containing 'name' and 'value' str keys, and optionally an 'inline' bool key

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            list[dict]: A list of dicts, each containing an embed field containing 'name' and 'value' str keys, and optionally an 'inline' bool key
        """
        return []
