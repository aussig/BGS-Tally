from importlib import import_module
from os import listdir, path

from bgstally.debug import Debug
from bgstally.formatters.base import BaseActivityFormatterInterface, FieldActivityFormatterInterface, TextActivityFormatterInterface
from bgstally.formatters.default import DefaultActivityFormatter
from bgstally.utils import all_subclasses

for module in listdir(path.join(path.dirname(__file__), "formatters")):
    if module[-3:] == '.py': import_module("bgstally.formatters." + module[:-3])
del module


class ActivityFormatterManager:
    """
    Handles the management of output formatters
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        # Create list of instances of each subclass of FormatterInterface
        self._formatters: dict[str: BaseActivityFormatterInterface] = {}

        for cls in all_subclasses(FieldActivityFormatterInterface) | all_subclasses(TextActivityFormatterInterface):
            instance: BaseActivityFormatterInterface = cls(bgstally)
            self._formatters[cls.__name__] = instance

        Debug.logger.info(f"formatters: {self._formatters}")


    def get_formatters(self) -> dict[str: str]:
        """Get the available formatters

        Returns:
            dict: key = formatter class name, value = formatter public name
        """
        result: dict = {}

        for class_name, class_instance in self._formatters.items():
            if class_instance.is_visible(): result[class_name] = class_instance.get_name()

        return result


    def get_formatter(self, class_name: str) -> BaseActivityFormatterInterface | None:
        """Get a specific formatter by its class name

        Args:
            name (str): The class name of the formatter

        Returns:
            BaseFormatterInterface | None: The formatter
        """
        return self._formatters.get(class_name)


    def get_default_formatter(self) -> DefaultActivityFormatter | None:
        """Get the default formatter

        Returns:
            DefaultFormatter | None: The formatter
        """
        return self.get_formatter(DefaultActivityFormatter.__name__)


    def get_current_formatter(self) -> BaseActivityFormatterInterface:
        """Get the currently selected activity formatter

        Returns:
            BaseActivityFormatterInterface: Activity Formatter
        """
        return self.get_formatter(self.bgstally.state.discord_formatter)
