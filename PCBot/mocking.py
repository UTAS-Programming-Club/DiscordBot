"""This module contains a partial console implementation of crescent."""

import asyncio
import crescent
import hikari
import inspect
from PCBot.pluginmanager import get_plugin_info

# TODO: Support more crescent features
# TODO: Add error checking for invalid plugin or command_index


class MockContext:
    """A partial console implementation of crescent.Context."""

    message_index = 0

    async def respond(self, output: str, ephemeral: bool = False):
        """Mock crescent.Context.respond with console."""
        self.message_index += 1
        if ephemeral:
            print('#', end='')
        else:
            print('', end='')
        print(f'{self.message_index}: {output}')

    async def edit(self, output: str):
        """Mock crescent.Context.edit with console."""
        print(f'*{self.message_index}: {output}')


def mock_command(crescent_client: crescent.Client, plugin: str,
                 command_index: int,
                 options: dict[str, str | bool] = {}) -> None:
    """Mock crescent plugin commands."""
    plugin_info = get_plugin_info(crescent_client.plugins)
    command = plugin_info[plugin][command_index]
    mocked_class = command.owner()
    mock_context = MockContext()

    print(f'Mocking {command.app_command.name} command from {plugin}\n')

    print('Command option values')
    for name in dir(mocked_class):
        # Filter out special attributes
        if name[:2] == '__' or name[-2:] == '__':
            continue

        # Cannot use getattr since ClassCommandOption defines __get__
        attr = inspect.getattr_static(mocked_class, name)

        # Filter out anything that is not a command option
        if type(attr) is not crescent.commands.options.ClassCommandOption:
            continue

        if attr.default == hikari.UNDEFINED:
            print(f'{name} has no default value', end='')
            if name not in options:
                print(
                  ' and none provided in options. Cannot continue mocking.'
                )
                return
            setattr(mocked_class, name, options[name])
        elif attr.type == hikari.OptionType.STRING:
            print(f'{name}: "{attr.default}"', end='')
            if name in options and type(options[name]) is str:
                print(f', replaced by "{options[name]}" from options')
                setattr(mocked_class, name, options[name])
            else:
                print()
                setattr(mocked_class, name, attr.default)
        else:
            print(f'{name}: {attr.default}', end='')
            if name in options:
                print(f', replaced by {options[name]} from options')
                setattr(mocked_class, name, options[name])
            else:
                print()
                setattr(mocked_class, name, attr.default)

    print('\nRunning command:')
    asyncio.run(mocked_class.callback(mock_context))
