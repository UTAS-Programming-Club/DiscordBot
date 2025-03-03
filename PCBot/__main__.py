"""This module starts the PC discord bot."""

from colorama import just_fix_windows_console
import crescent
import hikari
import miru
import sys
from hikari.intents import Intents
from PCBot.botdata import (
    BotData, token_path, lavalink_password_path,
    guild_id_path, get_token_file_path, ongaku_available
)
from PCBot.pluginmanager import reload_plugins
# from PCBot.testing.mocking import mock_command
# from PCBot.testing.hikari.test_users_comparision import (
#   make_interactions_member
# )

if ongaku_available:
    import ongaku

# Load bot token
with open(get_token_file_path(token_path)) as f:
    token = f.read().strip()

if sys.version_info.minor >= 11:
    with open(get_token_file_path(lavalink_password_path)) as f:
        lavalink_password = f.read().strip()

# Load guild id
with open(get_token_file_path(guild_id_path)) as f:
    guild_id = int(f.read().strip())

# Create bot
# GUILD_MESSAGES is required for miru
# default_guild is needed to get register_commands to do a guild specific push
bot = hikari.GatewayBot(
    token, force_color=True,
    intents=Intents.GUILDS | Intents.GUILD_MESSAGES
            | hikari.Intents.GUILD_VOICE_STATES | Intents.MESSAGE_CONTENT
)
miru_client = miru.Client(bot)

if ongaku_available:
    ongaku_client = ongaku.Client(bot, password=lavalink_password)
    model = BotData(miru_client, ongaku_client)
else:
    model = BotData(miru_client)
crescent_client = crescent.Client(bot, model, default_guild=guild_id)


async def load_plugins():
    """Load working plugins while ignoring others."""
    try:
        await reload_plugins(crescent_client.plugins, 'PCBot.plugins')
    finally:
        await crescent_client.commands.register_commands()


# Load plugins
# For mocking
# crescent_client.plugins.load_folder('PCBot.plugins')
# For running the bot
crescent_client._run_future(load_plugins())

# TODO: Fix
# plugin_info = get_plugin_info(crescent_client.plugins)
# print_plugin_info(plugin_info)

# Run the bot
if __name__ == '__main__':
    just_fix_windows_console()
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

    # info_public = True
    # Test info command
    # mock_command(crescent_client, 'PCBot.plugins.info', 0, options={
    #   'public': info_public
    # })

    # Test text adventure command
    # mock_command(crescent_client, 'PCBot.plugins.textadventure', 0,
    #              options={}
    # )
