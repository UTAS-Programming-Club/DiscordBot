"""This module contains the bot's text adventure command."""

import crescent
import hikari
import os.path
from cffi import FFI
from crescent.ext import docstrings

if not os.path.isfile('GameData.json') or not os.path.isfile('game.so'):
    raise Exception('Unable to find required game files')

plugin = crescent.Plugin[hikari.GatewayBot, None]()

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
""")
game = ffi.dlopen("./game.so")


@plugin.include
@docstrings.parse_doc
@crescent.command(name='text')
class TextCommand:
    """
    Start the PC's untitled text adventure.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    async def handle_output(self, ctx: crescent.Context, output):
        """Get and respond with the current game state."""
        succeeded: bool = game.GetCurrentGameOutput(output)
        if (not succeeded):
            await ctx.respond("Unable to get game output")
            return

        response = ('```' + ffi.string(output.body) + '```'
                    + '\nIn future the following options will be available:\n')
        for i in range(output.inputCount):
            input_str = ffi.string(output.inputs[i].title)
            response += f'{i + 1}. {input_str}\n'

        await ctx.respond(response)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle text command being run."""
        if (not game.SetupGame()):
            await ctx.respond("Unable to start game")
            return

        output = ffi.new("struct GameOutput *")
        await self.handle_output(ctx, output)
