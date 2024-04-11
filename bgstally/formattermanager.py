from importlib import import_module
from os import listdir, path

from bgstally.debug import Debug
from bgstally.formatters.base import BaseFormatterInterface, FieldFormatterInterface, TextFormatterInterface
from bgstally.formatters.default import DefaultFormatter
from bgstally.utils import all_subclasses

for module in listdir(path.join(path.dirname(__file__), "formatters")):
    if module[-3:] == '.py': import_module("bgstally.formatters." + module[:-3])
del module


class FormatterManager:
    """
    Handles the management of output formatters
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        # Create list of instances of each subclass of FormatterInterface
        self._formatters: dict[str: BaseFormatterInterface] = {}

        for cls in all_subclasses(FieldFormatterInterface) | all_subclasses(TextFormatterInterface):
            instance: BaseFormatterInterface = cls(bgstally.state)
            self._formatters[cls.__name__] = instance

        Debug.logger.info(f"formatters: {self._formatters}")


    def get_formatters(self) -> dict[str: str]:
        """Get the available formatters

        Returns:
            dict: key = formatter class name, value = formatter public name
        """
        return ({class_name: class_instance.get_name() for class_name, class_instance in self._formatters.items()})


    def get_formatter(self, class_name: str) -> BaseFormatterInterface | None:
        """Get a specific formatter by its class name

        Args:
            name (str): The class name of the formatter

        Returns:
            BaseFormatterInterface | None: The formatter
        """
        return self._formatters.get(class_name)


    def get_default_formatter(self) -> DefaultFormatter | None:
        """Get the default formatter

        Returns:
            DefaultFormatter | None: The formatter
        """
        return self.get_formatter("DefaultFormatter")
