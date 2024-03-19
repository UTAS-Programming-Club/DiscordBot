"""This module contains functions used to load and manage plugins."""

import crescent
import importlib
import logging
import sys
import traceback
from collections import Counter
from pathlib import Path

# TODO: Log plugin instead instead of directly printing
# TODO: Keep reloading after failure in one file

logger = logging.getLogger(__name__)


def get_plugin_names(plugin_manager: crescent.PluginManager) -> Counter[str]:
    """Provide a list of loaded plugins."""
    return Counter(plugin_manager.plugins.keys())


# This is not a good method since it uses crescent's internal api but I could
# not find another way to access command info without manually finding all
# classes and functions with plugin.include which I assume is possible
def get_plugin_info(plugin_manager: crescent.PluginManager)\
 -> dict[str, tuple[crescent.internal.AppCommand]]:
    """Provide a list of loaded plugins along with their commands."""
    loaded_commands: dict[str, tuple[crescent.internal.AppCommand]] = {}
    for plugin_name, plugin in plugin_manager.plugins.items():
        loaded_commands[plugin_name] = tuple([
            child.metadata.app_command for child in plugin._children
        ])
    return loaded_commands


def print_plugin_info(
    plugin_info: dict[str, tuple[crescent.internal.AppCommand]]
) -> None:
    """Print the name of each plugin along with their commands."""
    for plugin_name, commands in plugin_info.items():
        print(plugin_name)
        for command in commands:
            print(f'    {command.name}: {command.description}')


def reload_plugin_manager() -> None:
    """Reload this module."""
    module = importlib.import_module(__name__)
    importlib.reload(module)


def reload_plugin(
    plugin_manager: crescent.PluginManager, path: str, strict: bool = True
) -> None:
    """Reload a single plugin with error reporting but no exceptions."""
    try:
        plugin_manager.load(path, strict=strict)
        plugin_manager.load(path, refresh=True, strict=strict)
    except:
        # From https://stackoverflow.com/a/45771867
        # Try to find first trace line within erroring plugin
        spec = importlib.util.find_spec(path)
        if spec is None:
            # If failed to find plugin then just print entire traceback
            print(traceback.format_exc())
        else:
            file_name = spec.loader.get_filename()
            extracts = traceback.extract_tb(sys.exc_info()[2])
            count = len(extracts)
            # Find the first occurrence of the plugin file name
            for i, extract in enumerate(extracts):
                if extract[0] == file_name:
                    break
                count -= 1
            traceback_output = traceback.format_exc(limit=-count)
            logger.error('The following error occurred while loading' + path)
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
            print('test')


# From https://github.com/hikari-crescent/hikari-crescent/blob/v0.6.6/crescent/plugin.py
# Afaik I can use this despite an incompatable licence with mpl provided this
# fuction(file?) remains under mpl since it is "Covered Software" by 3.3 and
# then mention Exhibit B
async def reload_plugins(
    plugin_manager: crescent.PluginManager, path: str, strict: bool = True
) -> None:
    """Load new plugins, reloads existing ones and unload old ones."""
    pathlib_path = Path(*path.split("."))

    # Used to avoid the a load erroring because it tried to load
    # an already loaded plugin
    plugin_manager.unload_all()

    for glob_path in sorted(pathlib_path.glob(r'**/[!_]*.py')):
        plugin_path = ".".join(glob_path.as_posix()[:-3].split("/"))
        reload_plugin(plugin_manager, plugin_path)
