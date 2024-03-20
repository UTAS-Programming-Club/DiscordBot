"""This module contains the bot's plugin help command."""

import crescent
import hikari
import inspect
from crescent.ext import docstrings
from PCBot.pluginmanager import get_plugin_info

# TODO: Provide per command help that shows the entire docstring.

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

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle help command being run."""
        plugin_info = get_plugin_info(plugin.client.plugins)
        output = help_start + '\n'

        name_lens = [
          len(command.name)
          for plugin_name in plugin_info
          for command in plugin_info[plugin_name]
        ]
        longest_name_len = max(full_name_list)

        for plugin_name, commands in plugin_info.items():
            output = output + f'    {plugin_name}:\n'
            for command in sorted(commands):
                output = output + (f'        {command.name:{longest_name_len}}'
                                   f'    {command.description}\n')

        output = output + '```'
        await ctx.respond(output, ephemeral=True)
