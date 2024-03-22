"""This module starts the PC discord bot."""

import crescent
import hikari
import miru
from PCBot.botdata import (
    BotData, token_path, guild_id_path, get_token_file_path
)
from PCBot.pluginmanager import get_plugin_info, print_plugin_info
# from PCBot.testing.mocking import mock_command
# from PCBot.testing.hikari.test_users_comparision import (
#   make_interactions_member
# )

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

    # These make testing the bot easier since they don't require reloading or
    # restarting the bot and then messing around with discord to run a command

    # help_public = True
    # Test basic help command
    # mock_command(crescent_client, 'PCBot.plugins.help', 0, options={
    #   'public': help_public
    # })

    # Test command help command
    # mock_command(crescent_client, 'PCBot.plugins.help', 0, options={
    #    'public': help_public, 'command': 'rpschallenge'
    # })

    # Test reload command
    # Cannot reregister as crescent.internal.registry.register_commands does
    # not work without the bot running
    # reload_list_plugins = True
    # mock_command(crescent_client, 'PCBot.plugins.reload', 0, options={
    #     'list_plugins': reload_list_plugins, 'reregister': False
    # })

    # Test rpschallenge
    # Only gets as far as reponding with components as MockContext does not
    # (yet?) support components
    # mock_command(crescent_client, 'PCBot.plugins.rockpaperscissors', 0,
    #              options={
    #   'user': make_interactions_member(crescent_client.app, 2, 'testuser2')
    # })
