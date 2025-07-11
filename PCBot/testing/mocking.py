"""This module contains a partial console implementation of crescent."""

import asyncio
import crescent
import hikari
import inspect
from colorama import Style
from PCBot.pluginmanager import get_plugin_info
from PCBot.testing.hikari.test_users_comparision import (
  make_interactions_member, make_user
)
from typing import Optional

# TODO: Support more crescent features
# TODO: Add error checking for invalid plugin or command_index
# TODO: Check types of other builtins before using setattr

last_id = 0

class MockMessage:
    """A partial console implementation of hikari.messages.Message."""
    id: int

    def __init__(self, id: int):
        self.id = id

    async def edit(self, output: str):
        print(f'*{self.id}: {output}')


class MockRestClient:
    """A partial console implementation of hikari.api.rest.RESTClient."""
    async def fetch_channel(
      self,
      channel: hikari.snowflakes.SnowflakeishOr[hikari.channels.PartialChannel]
    ) -> None:
        pass


class MockApp: # (hikari.traits.CacheAware):
    """A partial console implementation of hikari.impl.gateway_bot."""
    # _cache: hikari.api.cache.Cache
    rest: MockRestClient

    def __init__(self):
        # settings = hikari.impl.config.CacheSettings()
        # self._cache = hikari.impl.cache.CacheImpl(self, settings)
        self.rest = MockRestClient()

    # @property
    # def cache(self) -> hikari.api.cache.Cache:
    #     return self._cache


class MockContext:
    """A partial console implementation of crescent.Context."""

    app: MockApp
    channel_id: hikari.snowflakes.Snowflake
    user: hikari.users.UserImpl

    # Mock specific
    last_message_id: Optional[int] = None

    def __init__(self, app: hikari.traits.RESTAware):
        """Create mock context, currently only user is mocked."""
        global last_id
        self.app = MockApp()
        self.channel_id = hikari.snowflakes.Snowflake(last_id + 1)
        self.user = make_user(app, last_id + 2, 'testuser1')
        last_id += 2

    async def defer(self, ephemeral: bool = False) -> None:
        return None

    async def respond(self, output: str, ephemeral: bool = False, ensure_message: bool = False) -> MockMessage:
        """Mock crescent.Context.respond with console."""
        global last_id
        last_id += 1
        if ephemeral:
            print('#', end='')
        else:
            print(' ', end='')
        print(f'{last_id}: {output}{Style.RESET}')
        last_message_id = last_id
        return MockMessage(last_id)

    async def respond_with_builder(self, builder: crescent.context.context.ResponseBuilderT, ensure_message: bool = False) -> MockMessage:
        global last_id
        last_id += 1
        print(f'{last_id}: {builder.content}{Style.RESET_ALL}')
        print('\nbuttons: ')
        for row in builder.components:
            buttons = [
                component.label for component in row.components
                if isinstance(component, hikari.impl.special_endpoints.InteractiveButtonBuilder)
            ]
            print(', '.join(buttons))
        last_message_id = last_id
        return MockMessage(last_id)

    async def edit(self, output: str) -> None:
        """Mock crescent.Context.edit with console."""
        if not self.last_message_id:
            raise Exception("Edit called without first calling respond")
        print(f'*{self.last_message_id}: {output}')


def mock_command(crescent_client: crescent.Client, plugin: str,
                 command_index: int,
                 options: dict[str, str | bool] = {}) -> None:
    """Mock crescent plugin commands."""
    plugin_info = get_plugin_info(crescent_client.plugins)
    command = plugin_info[plugin][command_index]
    mocked_class = command.owner()
    mock_context = MockContext(crescent_client.app)

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

def make_guild_member(
  app: hikari.traits.RESTAware, username: str
) -> hikari.interactions.base_interactions.InteractionMember:
  global last_id
  last_id += 1
  return make_interactions_member(app, last_id - 1, username)
