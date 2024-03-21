"""This module starts the PC discord bot."""

import crescent
import hikari
import miru
from PCBot.botdata import (
    BotData, token_path, guild_id_path, get_token_file_path
)
from PCBot.mocking import mock_command
from PCBot.pluginmanager import get_plugin_info, print_plugin_info

# TODO: Decide if loading in safe mode is allowed, reuse code from reload.py

# Load bot token
with open(get_token_file_path(token_path)) as f:
    token = f.read().strip()

# Load guild id
with open(get_token_file_path(guild_id_path)) as f:
    guild_id = int(f.read().strip())

# Create bot
# GUILD_MESSAGES is required for miru
# default_guild is needed to get register_commands to do a guild specific push
bot = hikari.GatewayBot(token, intents=hikari.Intents.GUILD_MESSAGES)
miru_client = miru.Client(bot)
crescent_client = crescent.Client(bot, BotData(miru_client),
                                  default_guild=guild_id)

# Load plugins
crescent_client.plugins.load_folder('PCBot.plugins')
plugin_info = get_plugin_info(crescent_client.plugins)
print_plugin_info(plugin_info)

# Run the bot
if __name__ == '__main__':
    bot.run()
    #mock_command(crescent_client, 'PCBot.plugins.help', 0,
    #             {'command': 'rpschallenge'})
