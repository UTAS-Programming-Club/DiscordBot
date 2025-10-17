"""This module contains the bot's plugin local testing command."""

from PCBot.pluginmanager import get_command_choices, get_plugin_info
from crescent import AutocompleteContext, command, Context, option, Plugin
from crescent.internal import handle_resp
from hikari import ApplicationContextType, AutocompleteInteractionOption, GatewayBot
from hikari.events import CommandInteractionCreateEvent
from hikari.interactions import CommandInteraction
from logging import getLogger
# from typing import Optional

# TODO: Reload botdata.py, only if can be done without losing data
# TODO: Restrict command to committee members
# TODO: Indicate which commands are from each plugin
# TODO: Indicate which plugins/commands are modified, modified or malformed
# TODO: Specifically list which exceptions are possible during plugin loading
# TODO: Change client status during reload?
# TODO: Prevent unloading reload command if on disk version has an error
# TODO: Report plugins that failed to load to whoever executed the command
# TODO: Add backup for if reload.py and pluginmanager.py fail? Restart command?

logger = getLogger(__name__)
plugin = Plugin[GatewayBot, None]()

async def command_autocomplete(
  ctx: AutocompleteContext,
  option: AutocompleteInteractionOption
) -> list[tuple[str, str]]:
    """Generate a list of commands for option autocomplete."""
    return get_command_choices(plugin.client.plugins)


@plugin.include
@command(name='local', description='Run unpublished local command.')
class LocalCommand:
    extra_description = """
    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    command = option(str, 'Command to run', autocomplete=command_autocomplete)

    async def callback(self, ctx: Context) -> None:
        """Handle local command being run."""

        plugin_info: dict[str, tuple[AppCommandMeta, ...]] = get_plugin_info(plugin.client.plugins)
        command_info: dict[str, AppCommandMeta] = {
          command.app_command.name: command
          for plugin_name in plugin_info
          for command in plugin_info[plugin_name]
        }

        if self.command not in command_info:
            await ctx.respond(f'{self.command} is not a valid command.',
                              ephemeral=True)
            return

        command: AppCommandMeta = command_info[self.command]

        any_option_required = False
        for option in command.app_command.options:
            any_option_required |= option.is_required

        if any_option_required:
            await ctx.respond(f'{self.command} has required parameters which are not currently supported.',
                              ephemeral=True)
            return

        intr = CommandInteraction(
            app=ctx.app,
            app_permissions=None, # TODO: Set correctly
            application_id=ctx.application_id,
            authorizing_integration_owners={}, # TODO: Set correctly
            channel=ctx.channel,
            command_id=command.app_command.id,
            command_name=command.app_command.name,
            command_type=command.app_command.type,
            context=ApplicationContextType.GUILD, # TODO: Check this
            entitlements=ctx.entitlements,
            guild_id=ctx.guild_id,
            guild_locale=None, # TODO: Set correctly
            id=ctx.id,
            locale=ctx.locale,
            member=ctx.member,
            options=None, # TODO: Set correctly
            registered_guild_id=ctx.registered_guild_id,
            resolved=None, # TODO: Set correctly
            token=ctx.token,
            type=ctx.type,
            user=ctx.user,
            version=ctx.version,
        )
        await handle_resp(plugin.client, intr, None)
