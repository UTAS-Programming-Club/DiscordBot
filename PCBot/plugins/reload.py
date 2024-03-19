"""This module contains the bot's plugin reloading command."""

import crescent
import hikari
import logging
from crescent.ext import docstrings
from PCBot.botdata import BotData
from PCBot.pluginmanager import (
    get_plugin_names, reload_plugin_manager, reload_plugins
)
from typing import Optional

# TODO: Reload botdata.py, only if can be done without losing data
# TODO: Restrict command to committee members
# TODO: Indicate which commands are from each plugin
# TODO: Indicate which plugins/commands are modified, modified or malformed
# TODO: Specifically list which exceptions are possible during plugin loading
# TODO: Change client status during reload?
# TODO: Name file causing error, log currently says it occurred in this module
# TODO: Reenable error reporting, it only catches errors in pluginmanager now
# TODO: Report loading errors again, pluginmanager ignores them
# TODO: Prevent unloading reload command if on disk version has an error

logger = logging.getLogger(__name__)
plugin = crescent.Plugin[hikari.GatewayBot, BotData]()
plugin_folder = 'PCBot.plugins'


@plugin.include
@docstrings.parse_doc
@crescent.command(name='reload')
class ReloadCommand:
    """
    Reload the bot.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    list_plugins = crescent.option(bool, 'Show a list of loaded plugins?',
                                   default=False)
    reregister = crescent.option(bool, 'Reregister commands with discord.',
                                 default=True)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle reload command being run."""
        safe_mode: bool
        malformed_plugin_path: Optional[str] = None
        reloaded_text: str

        await ctx.respond('Reloading...', ephemeral=True)

        plugins = plugin.client.plugins
        old_plugins = get_plugin_names(plugins)

        try:
            reload_plugin_manager()
            await reload_plugins(plugins, plugin_folder)
            safe_mode = False
        except Exception as error:
            # Try to find first exception in erroring plugin
            # tb = error.__traceback__
            #  First error is in this file so not wanted despite passing check
            # if tb is not None:
            #     tb = tb.tb_next
            # while tb is not None:
            #     plugin_path = tb.tb_frame.f_code.co_filename
            #     if 'PCBot' not in plugin_path:
            #         tb = tb.tb_next
            #         continue
            #     base_name = os.path.basename(plugin_path)
            #     if 'pluginmanager' not in base_name:
            #         malformed_plugin_path = base_name.split('.')[0]
            #     break
            plugins.unload(__name__)
            plugins.load(__name__)
            plugins.load(__name__, refresh=True)
            safe_mode = True
            logger.error(error)

        if safe_mode and malformed_plugin_path is not None:
            reloaded_text = \
              f'Reloaded in safe mode, error in {malformed_plugin_path} plugin'
            logger.warning(reloaded_text)
            await ctx.edit(reloaded_text)
        elif safe_mode:
            reloaded_text = 'Reloaded in safe mode'
            logger.warning(reloaded_text)
            await ctx.edit(reloaded_text)
        else:
            reloaded_text = 'Reloaded'
            logger.info(reloaded_text)
            await ctx.edit(reloaded_text)

        new_plugins = get_plugin_names(plugins)
        loaded_list = ', '.join(new_plugins)
        missing_list = ', '.join(old_plugins - new_plugins)
        new_list = ', '.join(new_plugins - old_plugins)

        logger.info(f'Loaded plugins: {loaded_list}')
        if missing_list != '':
            logger.warning(f'Missing plugins: {missing_list}')
        if new_list != '':
            logger.info(f'New plugins: {new_list}')
        if self.list_plugins:
            await ctx.respond(f'Loaded plugins: {loaded_list}')

        # Reregister commands with discord
        if self.reregister:
            await ctx.edit(reloaded_text + ', Reregistering')

            await plugin.client.commands.register_commands()

            logger.info('Reregistered commands')
            await ctx.edit(reloaded_text + ', Reregistered')
