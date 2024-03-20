"""This module contains the bot's plugin help command."""

import crescent
import hikari
import inspect
from crescent.ext import docstrings
from PCBot.pluginmanager import get_plugin_info

# TODO: Add sorting to commands

plugin = crescent.Plugin[hikari.GatewayBot, None]()

help_start = inspect.cleandoc('''```
  PCBot help:
  This is a bot designed by members of the UTas Programming Club.

  Available plugins and commands:''')


@plugin.include
@docstrings.parse_doc
@crescent.command(name='help')
class HelpCommand:
    """
    Provide infomation about available commands.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    public = crescent.option(bool, 'Show response publicly', default=False)
    command = crescent.option(str, 'Show detailed info for a single command',
                              default='')

    async def basic_help(self, ctx: crescent.Context) -> None:
        """Show a list of plugins and commands."""
        plugin_info = get_plugin_info(plugin.client.plugins)
        output = help_start + '\n'

        name_lens = [
          len(command.app_command.name)
          for plugin_name in plugin_info
          for command in plugin_info[plugin_name]
        ]
        longest_name_len = max(name_lens)

        for plugin_name, commands in plugin_info.items():
            output = f'{output}    {plugin_name}:\n'
            for command in commands:
                app_command = command.app_command
                output = (
                  f'{output}        {app_command.name:{longest_name_len}}'
                  f'    {app_command.description}\n'
                )

        output = output + '```'
        await ctx.respond(output, ephemeral=not self.public)

    async def command_help(self, ctx: crescent.Context) -> None:
        """Show detailed info for a single command."""
        plugin_info = get_plugin_info(plugin.client.plugins)
        output = f'```PCBot help:\n\n{self.command} command info:\n'

        command_info = {
          command.app_command.name: command
          for plugin_name in plugin_info
          for command in plugin_info[plugin_name]
        }

        if self.command not in command_info:
            await ctx.respond(f'{self.command} is not a valid command.',
                              ephemeral=True)
            return

        command = command_info[self.command]
        output = (f'{output}This command is a part of '
                  f'{command.owner.__module__}.\n')

        if command.owner.__doc__ is not None:
            output = f'{output}Description: {inspect.getdoc(command.owner)}'
        elif command.app_command.description != 'No Description':
            output = f'{output}Description: {command.app_command.description}'
        else:
            output = (
              f'{output}No additional infomation was provided for this'
              'command.'
            )

        output = output + '```'
        await ctx.respond(output, ephemeral=not self.public)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle help command being run."""
        if self.command == '':
            await self.basic_help(ctx)
        else:
            await self.command_help(ctx)
