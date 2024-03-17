import crescent
import hikari
import logging
from crescent.ext import docstrings

# TODO: Prevent error when loading unloaded plugin, issue with refresh?

# Load guild id
with open('./secrets/guild') as f:
  guildId = int(f.read().strip())

plugin = crescent.Plugin[hikari.GatewayBot, None]()

@plugin.include
@docstrings.parse_doc
@crescent.command(guild = guildId)
async def reload(ctx: crescent.Context) -> None:
  """
  Reload the bot.
  
  Requested by something sensible(somethingsensible).
  Implemented by something sensible(somethingsensible).
  """
  await ctx.respond('Reloading...', ephemeral = True)
  plugins = plugin.client.plugins
  # TODO: Fix this causing errors or not actually loading any plugin changes
  # The current issue is that this copy of load_folder will error if an unloaded
  # plugin is detected either because it is new or it errored on a previous load
  #plugins.unload_all()
  plugins.load_folder('PCBot.plugins', refresh = True)
  await ctx.edit('Reloaded')
  logging.getLogger(__name__).info("Reloaded")
