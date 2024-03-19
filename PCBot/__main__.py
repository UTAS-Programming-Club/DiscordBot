"""This module starts the PC discord bot."""

import crescent
import hikari
import miru
from PCBot.botdata import BotData

# TODO: Decide if loading in safe mode is allowed, reuse code from reload.py
# TODO: Report loaded commands/modules to the console.

# Load bot token
with open('./secrets/token') as f:
    token = f.read().strip()

# Create bot
# GUILD_MESSAGES is required for miru
bot = hikari.GatewayBot(token, intents=hikari.Intents.GUILD_MESSAGES)
miru_client = miru.Client(bot)
crescent_client = crescent.Client(bot, BotData(miru_client))

# Load plugins
loaded_plugins = crescent_client.plugins.load_folder('PCBot.plugins')

# Run the bot
if __name__ == '__main__':
    bot.run()
