from bgstally.activity import Activity
from bgstally.constants import DiscordActivity
from bgstally.state import State


class FormatterInterface:
    """The interface for all discord formatters. Every formatter should implement this interface
    """

    def __init__(self, state: State):
        """Instantiate class

        Args:
            state (State): The State object containing persistent values and settings
        """
        self.state: State = state


    def generate_text(self, activity: Activity, activity_mode: DiscordActivity, discord: bool = False, system_names: list = None, lang: str = None) -> str:
        """Generate formatted text for a given instance of Activity

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            discord (bool, optional): True if the destination is Discord (so can include Discord-specific formatting such
            as ```ansi blocks and UTF8 emoji characters), False if not. Defaults to False.
            system_names (list, optional): A list of system names to restrict the output for. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            str: The output
        """
        pass


    def generate_embed_fields(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> list[dict]:
        """Generate a list of discord embed fields, conforming to the embed field spec defined here:
        https://birdie0.github.io/discord-webhooks-guide/structure/embed/fields.html - i.e. each field should be a dict
        containing 'name' and 'value' str keys, and optionally an 'inline' bool key

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            list: A list of fields
        """
        pass
