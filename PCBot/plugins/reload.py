"""This module contains the bot's plugin reloading command."""

import crescent
import hikari
import logging
import sys
from crescent.ext import docstrings

# TODO: Fix newly loaded plugins not showing up in discord
# TODO: Restrict command to committee members
# TODO: Indicate which commands are from each plugin
# TODO: Indicate which plugins/commands are new, modified or unmodified

# Load guild id
with open('./secrets/guild') as f:
    guild_id = int(f.read().strip())

logger = logging.getLogger(__name__)
plugin = crescent.Plugin[hikari.GatewayBot, None]()


@plugin.include
@docstrings.parse_doc
@crescent.command(guild=guild_id)
async def reload(ctx: crescent.Context) -> None:
    """
    Reload the bot.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """
    await ctx.respond('Reloading...', ephemeral=True)

    # Used to avoid an error with plugin being undefined after unload_all
    plugins = plugin.client.plugins
    # Used to avoid the first load_folder erroring because it tried to load an
    # already loaded plugin
    plugins.unload_all()
    # Load unloaded plugins, if any plugin it finds was previously loaded then
    # the old code is reused
    plugins.load_folder('PCBot.plugins')
    # Reload previously loaded plugins to use newest code
    new_plugins = plugins.load_folder('PCBot.plugins', refresh=True)

    logger.info("Reloaded")
    await ctx.edit('Reloaded')

    loaded_plugin_names = tuple([
        module_name.split('.')[-1]
        for module_name, module in sys.modules.items()
        if 'PCBot.plugins.' in module_name
        if getattr(module, "plugin", None) in new_plugins
    ])
    logger.info(f"Loaded plugins: {', '.join(loaded_plugin_names)}")
    await ctx.respond(f"Loaded plugins: {', '.join(loaded_plugin_names)}")
