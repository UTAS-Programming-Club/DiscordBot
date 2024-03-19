"""This module contains functions used to load and manage plugins."""

import crescent
import logging
import traceback
from collections import Counter
from importlib import import_module, reload
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
    module = import_module(__name__)
    reload(module)


def reload_plugin(
    plugin_manager: crescent.PluginManager, path: str, strict: bool = True
) -> None:
    """Reload a single plugin with error reporting but no exceptions."""
    try:
        plugin_manager.load(path, strict=strict)
        plugin_manager.load(path, refresh=True, strict=strict)
    except Exception as error:
        # Try to find first exception in erroring plugin
        tb = error.__traceback__
        # First error is in this file which is not wanted despite
        # passing path check
        if tb is not None:
            tb = tb.tb_next
        while tb is not None:
            plugin_path = tb.tb_frame.f_code.co_filename
            if 'PCBot' not in plugin_path:
                tb = tb.tb_next
                continue
            traceback.print_tb(tb)
            break
        logger.error(error)


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
        print(glob_path)
