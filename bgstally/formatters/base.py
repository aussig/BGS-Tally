from abc import ABC, abstractmethod

from bgstally.activity import Activity
from bgstally.constants import DiscordActivity, DiscordPostStyle
from bgstally.utils import _


class BaseActivityFormatterInterface(ABC):
    """The base interface for discord formatters
    """

    def __init__(self, bgstally):
        """Instantiate class

        Args:
            bgstally (BGSTally): The BGSTally object
        """
        self.bgstally = bgstally


    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this formatter

        Returns:
            str: The name of this formatter for choosing in the UI
        """
        pass


    @abstractmethod
    def get_mode(self) -> DiscordPostStyle:
        """Get the output format mode that this Formatter supports

        Returns:
            DiscordPostStyle: The supported discord post mode
        """
        pass


    def is_visible(self) -> bool:
        """Should this formatter be visible to the user as a choice

        Returns:
            bool: True if visible, false if not
        """
        return True


    @abstractmethod
    def get_text(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> str:
        """Generate formatted text for a given instance of Activity. Must be implemented by subclasses.
        This method is used for getting the text for the 'copy and paste' function, and for direct posting
        to Discord for those Formatters that use text style posts (vs Discord embed style posts)

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            str: The output text
        """
        pass


    def get_preview(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> str:
        """Get the activity window preview for a given instance of Activity. The on-screen previewer
        in BGS-Tally uses ANSI colour codes so this should return an ANSI-colour preview. By default
        just calls get_text() but if your Discord output is not ANSI-colour based (for example if it
        uses Discord's .css output instead) then you will need to override this method and either try
        to match it using ANSI output or simply return plain text which will not be coloured in the preview.

        Args:
            activity (Activity): _description_
            activity_mode (DiscordActivity): _description_
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): _description_. Defaults to None.

        Returns:
            str: _description_
        """
        return self.get_text(activity, activity_mode, system_names, lang)


class TextActivityFormatterInterface(BaseActivityFormatterInterface):
    """An activity formatter that returns text for displaying in Discord.

    It is not recommended to implement formatters based on this class, use a FieldFormatterInterface to build
    Discord posts that use the more modern-looking embed-based display
    """

    def get_mode(self) -> DiscordPostStyle:
        """Get the output format mode that this Formatter supports

        Returns:
            DiscordPostStyle: The supported discord post mode
        """
        return DiscordPostStyle.TEXT


class FieldActivityFormatterInterface(BaseActivityFormatterInterface):
    """An activity formatter that returns fields for displaying in a Discord embed.

    This is the recommended class to implement for new activity formatters, as field-based Discord posts are more modern
    looking, and consistent with posts from other functionality in BGS-Tally such as CMDR information posts and
    Fleet Carrier information posts.
    """

    def get_mode(self) -> DiscordPostStyle:
        """Get the output format mode that this Formatter supports

        Returns:
            DiscordPostStyle: The supported discord post mode
        """
        return DiscordPostStyle.EMBED


    @abstractmethod
    def get_fields(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> list[dict]:
        """Generate a list of discord embed fields, conforming to the embed field spec defined here:
        https://birdie0.github.io/discord-webhooks-guide/structure/embed/fields.html - i.e. each field should be a dict
        containing 'name' and 'value' str keys, and optionally an 'inline' bool key

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            list[dict]: A list of dicts, each containing an embed field containing 'name' and 'value' str keys, and optionally an 'inline' bool key
        """
        pass
