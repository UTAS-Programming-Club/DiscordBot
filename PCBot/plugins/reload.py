import crescent
import hikari
from crescent.ext import docstrings

plugin = crescent.Plugin[hikari.GatewayBot, None]()

@plugin.include
@docstrings.parse_doc
@crescent.command
async def reload(ctx: crescent.Context) -> None:
  """
  Reload the bot.
  """
  await ctx.respond("Reloading...")
  plugin.client.plugins.load_folder("PCBot.plugins", refresh=True)
