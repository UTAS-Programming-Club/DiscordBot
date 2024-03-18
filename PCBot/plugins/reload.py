"""This module contains the bot's plugin reloading command."""

import crescent
import hikari
import logging
import os
from crescent.ext import docstrings
from PCBot.botdata import BotData
from typing import Optional

# TODO: Reload botdata.py, only if can be done without losing data
# TODO: Fix newly loaded plugins not showing up in discord
# TODO: Restrict command to committee members
# TODO: Indicate which commands are from each plugin
# TODO: Indicate which plugins/commands are modified, modified or malformed
# TODO: Specifically list which exceptions are possible during plugin loading
# TODO: Change client status during reload?

# Load guild id
with open('./secrets/guild') as f:
    guild_id = int(f.read().strip())

logger = logging.getLogger(__name__)
plugin = crescent.Plugin[hikari.GatewayBot, BotData]()
plugin_folder = 'PCBot.plugins'


@plugin.include
@docstrings.parse_doc
@crescent.command(name='reload', guild=guild_id)
class ReloadCommand:
    """
    Reload the bot.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    list_plugins = crescent.option(bool, 'Show a list of loaded plugins?',
                                   default=False)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle reload command being run."""
        safe_mode: bool
        malformed_plugin_path: Optional[str] = None

        await ctx.respond('Reloading...', ephemeral=True)

        # Used to avoid an error with plugin being undefined after unload_all
        plugins = plugin.client.plugins
        # Used to avoid the first load_folder erroring because it tried to load
        # an already loaded plugin
        plugins.unload_all()
        # Load unloaded plugins, if any plugin it finds was previously loaded
        # then the old code is reused
        try:
            plugins.load_folder(plugin_folder)
            # Reload previously loaded plugins to use newest code
            loaded_plugins = plugins.load_folder(plugin_folder, refresh=True)
            safe_mode = False
        except Exception as error:
            # Try to find first exception in erroring plugin
            tb = error.__traceback__
            # First error is in this file so not wanted despite passing check
            if tb is not None:
                tb = tb.tb_next
            while tb is not None:
                plugin_path = tb.tb_frame.f_code.co_filename
                if 'PCBot' not in plugin_path:
                    tb = tb.tb_next
                    continue
                base_name = os.path.basename(plugin_path)
                malformed_plugin_path = base_name.split('.')[0]
                break
            # Used to prevent load erroring, not sure why unload_all fails here
            plugins.unload(__name__)
            plugins.load(__name__)
            loaded_plugins = [plugins.load(__name__, refresh=True)]
            safe_mode = True

        if safe_mode and malformed_plugin_path is not None:
            logger.warning(
              f'Reloaded in safe mode, error in {malformed_plugin_path} plugin'
            )
            await ctx.edit(
              f'Reloaded in safe mode, error in {malformed_plugin_path} plugin'
            )
        elif safe_mode:
            logger.warning('Reloaded in safe mode')
            await ctx.edit('Reloaded in safe mode')
        else:
            logger.info('Reloaded')
            await ctx.edit('Reloaded')

        old_plugins = plugin.model.plugin_names
        plugin.model.update_plugins(loaded_plugins)
        loaded_list = ', '.join(plugin.model.plugin_names)
        missing_list = ', '.join(old_plugins - plugin.model.plugin_names)
        new_list = ', '.join(plugin.model.plugin_names - old_plugins)

        logger.info(f'Loaded plugins: {loaded_list}')
        if missing_list != '':
            logger.warning(f'Missing plugins: {missing_list}')
        if new_list != '':
            logger.info(f'New plugins: {new_list}')
        if self.list_plugins:
            await ctx.respond(f'Loaded plugins: {loaded_list}')
