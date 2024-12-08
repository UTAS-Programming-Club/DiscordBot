"""This module contains the bot's updated text adventure command."""

# TODO: Fix PCGame script not being reloaded on bot reload

import crescent
from hikari import Message, MessageCreateEvent, GatewayBot
from hikari.snowflakes import Snowflake
from PCBot.PCGame import backend_ActionScreen, backend_GameState


plugin = crescent.Plugin[GatewayBot, None]()
games: dict[Snowflake, backend_GameState] = {}

async def handle_output(message: Message) -> None:
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

async def handle_input(message: Message, index: int) -> None:
    """Update the current game state given the last input."""
    game = games[message.id]

    if not isinstance(game.currentScreen, backend_ActionScreen):
        await message.edit('Unable to get current screen')
        return

    actions = game.currentScreen.GetActions(game)
    if index >= len(actions):
        return

    if not game.HandleGameInput(actions[index].type):
        await message.edit('Unable to process selected action')
        return

    await handle_output(message)

# TODO: Reuse hangman input method with thread support
@plugin.include
@crescent.event
async def on_game_message_create(event: MessageCreateEvent) -> None:
    """Handle users replying to game messages."""
    game_message = event.message.referenced_message
    if game_message is None:
        return

    if game_message.id not in games:
        return
    game = games[game_message.id]

    user_input = event.message.content.replace(' ', '')
    if not user_input.isdigit():
        return

    input_index = int(user_input) - 1

    await event.message.delete()
    await handle_input(game_message, input_index)

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
