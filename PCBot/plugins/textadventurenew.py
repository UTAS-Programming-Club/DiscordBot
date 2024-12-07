"""This module contains the bot's updated text adventure command."""

# TODO: Fix PCGame script not being reloaded on bot reload

import crescent
from hikari import Message, GatewayBot
from hikari.snowflakes import Snowflake
from PCBot.PCGame import backend_ActionScreen, backend_GameState


plugin = crescent.Plugin[GatewayBot, None]()
games: dict[Snowflake, backend_GameState] = {}

async def handle_output(message: Message):
    """Get and respond with the current game state."""
    game = games[message.id]

    if isinstance(game.currentScreen, backend_ActionScreen):
        response = ('```' + game.currentScreen.body + '```'
                    + '\nReply to this message with one of the numbers below '
                    + 'to choose that option:\n')

        actions = game.currentScreen.GetActions(game)
        for idx, action in enumerate(actions):
            response += f"{idx}. {action.title}"
    else:
        response = 'Unable to get current screen'
    await message.edit(response)

@plugin.include
@crescent.command(name='text2')
class TextCommand:
    """
    Start the PC's updated untitled text adventure.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle text command being run."""
        global games

        message = await ctx.respond('Setting up game', ensure_message=True)
        games[message.id] = backend_GameState()
        await handle_output(message)
