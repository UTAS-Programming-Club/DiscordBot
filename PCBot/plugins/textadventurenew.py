"""This module contains the bot's updated text adventure command."""

import crescent
from hikari import GatewayBot
from hikari.snowflakes import Snowflake
from PCBot.PCGame import backend_GameState


plugin = crescent.Plugin[GatewayBot, None]()
games: dict[Snowflake, backend_GameState] = {}

async def handle_output(message: hikari.Message):
    """Get and respond with the current game state."""
    game = games[message.id]

    response = '```' + game.currentScreen.body + '```'
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
