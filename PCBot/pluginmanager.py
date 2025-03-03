"""This module contains functions used to load and manage plugins."""

from collections import Counter
from crescent import Plugin, PluginManager
from crescent.internal import AppCommandMeta, Includable
from hikari import GatewayBot
from importlib import import_module, reload
from importlib.abc import ExecutionLoader, Loader
from importlib.machinery import ModuleSpec
from importlib.util import find_spec
from logging import getLogger, Logger
from pathlib import Path
from sys import exc_info
from traceback import extract_tb, format_exc, FrameSummary, StackSummary
from types import ModuleType
from typing import Any, Optional

# TODO: Avoid unloading reload.py
# TODO: Specifically list which exceptions are possible during plugin loading
# TODO: Use same error reporting in reload_plugin_manager as reload_plugin
# TODO: Fix the get_plugin_names() list being out of order while in safe mode
# TODO: Make get_plugin_info return be dict[str, dict[str, AppCommandMeta, ...]]?
#       This would make parts of help much easier to implement

logger: Logger = getLogger(__name__)


def get_plugin_names(plugin_manager: PluginManager) -> Counter[str]:
    """Provide a list of loaded plugins."""
    return Counter(plugin_manager.plugins.keys())


# This is not a good method since it uses crescent's internal api but I could
# not find another way to access command info without manually finding all
# classes and functions with plugin.include which I assume is possible
def get_plugin_info(plugin_manager: PluginManager)\
 -> dict[str, tuple[AppCommandMeta, ...]]:
    """Provide a list of loaded plugins along with their commands."""
    loaded_commands: dict[str, tuple[AppCommandMeta, ...]] = {}
    plugin_name: str
    plugin: Plugin[GatewayBot, Any]
    for plugin_name, plugin in plugin_manager.plugins.items():
        child: Includable[Any]
        loaded_commands[plugin_name] = tuple([
            child.metadata for child in plugin._children
            if type(child.metadata) == AppCommandMeta
        ])
    return loaded_commands


# TODO: Fix, only used in __main__ where plugin_info.items() is []
# def print_plugin_info(plugin_info: dict[str, tuple[AppCommand]]) -> None:
#     """Print the name of each plugin along with their commands."""
#     plugin_name: str
#     commands: tuple[AppCommand]
#     for plugin_name, commands in plugin_info.items():
#         print(plugin_name)
#         command: AppCommand
#         for command in commands:
#             app_command = command.app_command
#             print(f'    {app_command.name}: {app_command.description}')


# I planned to implement this using get_plugin_info but decided this was easier
def get_command_choices(plugin_manager: PluginManager)\
  -> list[tuple[str, str]]:
    """Provide a listed of loaded commands as crescent autocomplete tuples."""
    plugin: Plugin[GatewayBot, Any]
    child: list[Includable[Any]]
    return [
      (child.metadata.app_command.name, child.metadata.app_command.name)
      for plugin in plugin_manager.plugins.values()
      for child in plugin._children
    ]


def reload_plugin_manager() -> None:
    """Reload this module."""
    module: ModuleType = import_module(__name__)
    reload(module)


def reload_handlers(plugin_manager: PluginManager):
    """Reload plugins that provide functionally to other plugins."""
    if 'PCBot.plugins.replyhandler' not in plugin_manager.plugins.keys():
        return

    reply_handler: ModuleType = import_module('PCBot.plugins.replyhandler')
    reply_handler.reset_reply_handler()


def reload_plugin(
  plugin_manager: PluginManager, path: str, strict: bool = True
) -> None:
    """Reload a single plugin with error reporting but no exceptions."""
    try:
        plugin_manager.load(path, strict=strict)
        plugin_manager.load(path, refresh=True, strict=strict)
    except:
        logger.error(f'The following error occurred while loading {path}:')
        # From https://stackoverflow.com/a/45771867
        # Try to find first trace line within erroring plugin
        spec: Optional[ModuleSpec] = find_spec(path)
        if spec is None:
            # If failed to find plugin then just print entire traceback
            print(format_exc())
        else:
            loader: Optional[Loader] = spec.loader
            if not isinstance(loader, ExecutionLoader):
                # If failed to get data from loader then just print entire traceback
                print(format_exc())
                return
            file_name: str = loader.get_filename()  # pyright: ignore [reportCallIssue]
            extracts: StackSummary = extract_tb(exc_info()[2])
            count: int = len(extracts)
            # Find the first occurrence of the plugin file name
            extract: FrameSummary
            for extract in extracts:
                if extract[0] == file_name:
                    break
                count -= 1
            traceback_output: str = format_exc(limit=-count)
            # Some exceptions fail to display properly
            # This method with format_exc is actually the best method I have
            # found as iterating through a traceback with tb.tb_next actually
            # doesn't include the required line at the bottom, neither does
            # inspect.trace's list
            # So just missing the traceback line and some module info is
            # fine as I can work around it
            if not traceback_output.startswith('Traceback'):
                print('Traceback (most recent call last):')
            if traceback_output.endswith('\n'):
                traceback_output = traceback_output[:-1]
            print(traceback_output)


# From https://github.com/hikari-crescent/hikari-crescent/blob/v0.6.6/crescent/plugin.py
# Afaik I can use this despite an incompatable licence with mpl provided this
# fuction(file?) remains under mpl since it is "Covered Software" by 3.3 and
# then mention Exhibit B
async def reload_plugins(
    plugin_manager: PluginManager, path: str, strict: bool = True
) -> None:
    """Load new plugins, reloads existing ones and unload old ones."""
    pathlib_path = Path(*path.split("."))

    # Used to avoid the a load erroring because it tried to load
    # an already loaded plugin
    plugin_manager.unload_all()

    glob_path: Path
    for glob_path in sorted(pathlib_path.glob(r'**/[!_]*.py')):
        plugin_path: str = ".".join(glob_path.as_posix()[:-3].split("/"))
        reload_plugin(plugin_manager, plugin_path)
