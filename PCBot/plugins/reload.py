"""This module contains the bot's plugin reloading command."""

import crescent
import hikari
import logging
from crescent.ext import docstrings
from PCBot.pluginmanager import (
    get_plugin_names, reload_handlers, reload_plugin_manager, reload_plugins
)
from typing import Optional

# TODO: Reload botdata.py, only if can be done without losing data
# TODO: Restrict command to committee members
# TODO: Indicate which commands are from each plugin
# TODO: Indicate which plugins/commands are modified, modified or malformed
# TODO: Specifically list which exceptions are possible during plugin loading
# TODO: Change client status during reload?
# TODO: Prevent unloading reload command if on disk version has an error
# TODO: Report plugins that failed to load to whoever executed the command
# TODO: Add backup for if reload.py and pluginmanager.py fail? Restart command?

logger = logging.getLogger(__name__)
plugin = crescent.Plugin[hikari.GatewayBot, None]()
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
        # Safe mode was originally meant to be used whenever there was an error
        # while loading plugins and resulted in only the reload plugin being
        # available.
        # Currently, plugin load errors are only printed to the console and
        # keep all other plugins functional. Safe mode is therefore only used
        # where there is an error within reload.py or pluginmanager.py.
        # i.e. errors with loading plugins generally but not with a specific
        # one. Additionally, this leaves the state of plugins unpredictable
        # beyond the reload command being available. That is unless a second
        # error occurred during reloading the reload plugin in which case only
        # plugins that managed to be reloaded before the first error will work
        # and the bot will have to be restarted to be fully functional again.
        # In the event of the first kind of error, there are two main ways for
        # the resulting plugin state to be reported. The first is the loaded
        # plugin checks at the end of this method which lists which plugins are
        # still loaded and which are not. The second is that if both the
        # reregister option was set and crescent is still functional, the
        # loaded commands will be reregistered in discord. This second method
        # is currently the best method to confirm which commands are loaded
        # regardless of errors since even when working properly, only loaded
        # plugins are reported to the console or discord(with that option set).
        safe_mode: bool
        malformed_plugin_path: Optional[str] = None
        reloaded_text: str

        await ctx.respond('Reloading...', ephemeral=True)

        plugins = plugin.client.plugins
        old_plugins = get_plugin_names(plugins)

        try:
            reload_plugin_manager()
            reload_handlers(plugins)
            await reload_plugins(plugins, plugin_folder)
            safe_mode = False
        except:
            logger.exception('An error occurred while reloading plugins:')
            # reload_plugins unloads all plugins in which case load(refresh)
            # will error because it also unloads the plugin so need to do a
            # normal load first but that will fail if the error occurred before
            # unloading plugins or after the reload plugin was already reloaded
            # so need to unload it first which does nothing if it is not loaded
            plugins.unload(__name__)
            plugins.load(__name__)
            plugins.load(__name__, refresh=True)
            safe_mode = True

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
            await ctx.edit(reloaded_text + ', reregistering')

            await plugin.client.commands.register_commands()

            logger.info('Reregistered commands')
            await ctx.edit(reloaded_text + ', reregistered')
