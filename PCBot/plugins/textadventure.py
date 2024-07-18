"""This module contains the bot's text adventure command."""

import crescent
import hikari
import os.path
from cffi import FFI
from crescent.ext import docstrings
from enum import Enum
from typing import Any

if not os.path.isfile('GameData.json') or not os.path.isfile('game.so'):
    raise Exception('Unable to find required game files')

plugin = crescent.Plugin[hikari.GatewayBot, None]()
# TODO: Figure out type for cffi's "struct GameOutput *" and use instead of Any
games: dict[hikari.snowflakes.Snowflake, Any] = {}


class InputOutcome(Enum):
    """Represents the possible outcomes for different inputs."""

    InvalidInputOutcome = 0
    GetNextOutput = 1
    QuitGame = 2
    GotoScreen = 3


# TODO: Switch to other method so that including headers is allowed
ffi = FFI()
ffi.cdef("""
// From arena.h
    typedef struct Region Region;
    struct Region {
        Region *next;
        size_t count;
        size_t capacity;
        uintptr_t data[];
    };

    typedef struct {
        Region *begin, *end;
    } Arena;

// From types.h
    enum ScreenID {
        // ..
        InvaidScreenID = 65535
    };

    enum InputOutcome {
        InvalidInputOutcome = 0
        // ..
    };

// From game.h
    struct GameInput {
// public, safe to use outside of backend
        char32_t *title;
// implementation, do not use outside of backend
        bool titleArena;
    };

    struct GameOutput {
// public, safe to use outside of backend
        enum ScreenID screenID;
        char32_t *body;
        uint8_t inputCount;
        struct GameInput *inputs;
// implementation, do not use outside of backend
        Arena arena;
        bool bodyArena;
        bool inputsArrayArena;
        unsigned char *stateData;
    };

    bool SetupGame(void);
    bool GetCurrentGameOutput(struct GameOutput *);
    enum InputOutcome HandleGameInput(enum ScreenID, uint32_t);

// From screens.h
    void FreeScreen(struct GameOutput *);
""")
game = ffi.dlopen("./game.so")


async def handle_output(message: hikari.Message):
    """Get and respond with the current game state."""
    output = games[message.id]
    succeeded: bool = game.GetCurrentGameOutput(output)
    if (not succeeded):
        await message.edit("Unable to get game output")
        return

    response = ('```' + ffi.string(output.body) + '```'
                + '\nReply to this message with one of the numbers below to '
                + 'choose that option:\n')
    for i in range(output.inputCount):
        input_str = ffi.string(output.inputs[i].title)
        response += f'{i + 1}. {input_str}\n'

    await message.edit(response)


async def handle_input(message: hikari.Message, input_index: int):
    """Update the current game state given the last input."""
    output = games[message.id]

    outcome_value = game.HandleGameInput(output.screenID, input_index)
    outcome = InputOutcome(outcome_value)

    match outcome:
        case InputOutcome.GetNextOutput:
            game.FreeScreen(output)
            await handle_output(message)
        case InputOutcome.QuitGame:
            game.FreeScreen(output)
            await message.edit('The game is over!')


@plugin.include
@crescent.event
async def on_game_message_create(event: hikari.MessageCreateEvent):
    """Handle users replying to game messages."""
    if event.message.referenced_message is None:
        return
    game_message = event.message.referenced_message

    if game_message.author == hikari.undefined.UNDEFINED:
        return

    if game_message.author.id != plugin.app.get_me().id:
        return

    if game_message.id not in games:
        return
    game_output = games[game_message.id]

    user_input = event.message.content.replace(' ', '')
    if not user_input.isdigit():
        return

    input_index = int(user_input) - 1
    if input_index >= 255:  # Input index is a uint8_t in c
        return

    await event.message.delete()
    await handle_input(game_message, input_index)


@plugin.include
@docstrings.parse_doc
@crescent.command(name='text')
class TextCommand:
    """
    Start the PC's untitled text adventure.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle text command being run."""
        if (not game.SetupGame()):
            await ctx.respond("Unable to start game")
            return

        message = await ctx.respond('Setting up game', ensure_message=True)
        games[message.id] = ffi.new("struct GameOutput *")
        await handle_output(message)
