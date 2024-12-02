"""This module contains the bot's text adventure command."""

import crescent
import hikari
import os.path
from cffi import FFI
from crescent.ext import docstrings
from enum import Enum
from typing import Any, Optional

if (not os.path.isfile('GameData.json') or not os.path.isfile('game.so')
    or not os.path.isfile('libzstd.so')):
    raise Exception('Unable to find required game files')

plugin = crescent.Plugin[hikari.GatewayBot, None]()
# TODO: Figure out type for cffi's "struct GameOutput *" and use instead of Any
game_info: Optional[Any] = None
games: dict[hikari.snowflakes.Snowflake, Any] = {}


class InputOutcome(Enum):
    """Represents the possible outcomes for different inputs."""

    InvalidInputOutcome = 0
    GetNextOutput = 1
    QuitGame = 2


class ScreenInputType(Enum):
  InvalidScreenInputType = 0
  ButtonScreenInputType = 1
  TextScreenInputType = 2



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
    enum Screen {
        // ..
        InvaidScreenID = 65535
    };

    enum ScreenInputType {
        InvalidScreenInputType = 0
        // ..
    };

    enum InputOutcome {
        InvalidInputOutcome = 0
        // ..
    };

    enum CustomScreenCode {
        // ..
        InvalidCustomScreenCode = 65535
    };

    typedef uint_fast8_t PlayerStat;

    #define EquipmentTypeCount 7

    #define EquipmentCount 63 // EquipmentTypeCount * EquipmentPerTypeCount
    typedef uint_fast8_t EquipmentID;

// From game.h
    struct PlayerInfo {
        PlayerStat health;
        PlayerStat stamina;
        PlayerStat physAtk;
        PlayerStat magAtk;
        PlayerStat physDef;
        PlayerStat magDef;

    // Do not access directly, use functions in equipment.h
    // Equipment types: helmets, chest pieces, gloves, pants, boots, primary weapon, secondary weapon
        bool unlockedItems[EquipmentCount];
        EquipmentID equippedItems[EquipmentTypeCount];
    };

    struct GameInfo {
// public, safe to use outside of backend
        const char *name; // utf-8
// implementation, do not use outside of backend
        bool initialised;

        struct PlayerInfo defaultPlayerInfo;

        uint_fast8_t floorSize;
        struct RoomInfo *rooms;

        struct EquipmentInfo *equipment; // Length is EquipmentCount
};

    struct GameInput {
// public, safe to use outside of backend
        const char *title;
        bool visible;
// implementation, do not use outside of backend
        enum InputOutcome outcome;
    };

    struct GameState {
// public, safe to use outside of backend
        enum Screen screenID;
        char *body;

        enum ScreenInputType inputType;
        uint_fast8_t inputCount;
        struct GameInput *inputs;
        enum Screen previousScreenID;
        enum Screen nextScreenID;

        struct PlayerInfo playerInfo;
        const struct RoomInfo *roomInfo;
        bool startedGame;
// implementation, do not use outside of backend
        Arena arena;

        size_t stateDataSize;
        unsigned char *stateData;

        enum CustomScreenCode customScreenCodeID;
    };

    bool SetupBackend(struct GameInfo *);
    bool UpdateGameState(const struct GameInfo *, struct GameState *);
    enum InputOutcome HandleGameInput(const struct GameInfo *, struct GameState *, uint_fast8_t, const char *);
    void CleanupGame(struct GameState *);
    void CleanupBackend(struct GameInfo *);
""")
zstdlib = ffi.dlopen("./libzstd.so")
gamelib = ffi.dlopen("./game.so")


async def handle_output(message: hikari.Message):
    """Get and respond with the current game state."""
    game = games[message.id]

    succeeded: bool = gamelib.UpdateGameState(game_info, game)
    if (not succeeded):
        gamelib.CleanupGame(game)
        games.pop(message.id, None)
        await message.edit("Unable to get game state")
        return

    inputType = ScreenInputType(game.inputType)
    match inputType:
        case ScreenInputType.ButtonScreenInputType:
            response = ('```' + ffi.string(game.body).decode('utf-8') + '```'
                        + '\nReply to this message with one of the numbers below to '
                        + 'choose that option:\n')
            visible_button_idx = 0
            for i in range(game.inputCount):
                if game.inputs[i].visible:
                    input_str = ffi.string(game.inputs[i].title).decode('utf-8')
                    response += f'{visible_button_idx + 1}. {input_str}\n'
                    visible_button_idx += 1
        case ScreenInputType.TextScreenInputType:
            response = ('```' + ffi.string(game.body).decode('utf-8') + '```'
                        + '\nReply to this message to enter text.\n')

    await message.edit(response)


async def handle_input(message: hikari.Message, input_index: int, input_str: str):
    """Update the current game state given the last input."""
    game = games[message.id]

    empty_text = ffi.new("char[]", str.encode(input_str))
    outcome_value = gamelib.HandleGameInput(game_info, game, input_index, empty_text)
    outcome = InputOutcome(outcome_value)

    match outcome:
        case InputOutcome.GetNextOutput:
            await handle_output(message)
        case InputOutcome.QuitGame:
            gamelib.CleanupGame(game)
            games.pop(message.id, None)
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
    game = games[game_message.id]

    input_index = 0
    input_str = ''
    inputType = ScreenInputType(game.inputType)

    match inputType:
        case ScreenInputType.ButtonScreenInputType:
            user_input = event.message.content.replace(' ', '')
            if not user_input.isdigit():
                return

            input_index = int(user_input) - 1
            if input_index >= 255:  # Input index is a uint8_t in c
                return
        case ScreenInputType.TextScreenInputType:
            input_str = event.message.content

    await event.message.delete()
    await handle_input(game_message, input_index, input_str)


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
        global game_info
        global games

        if not game_info:
            game_info = ffi.new("struct GameInfo *")
            if (not gamelib.SetupBackend(game_info)):
                await ctx.respond("Unable to start game")
                return

        message = await ctx.respond('Setting up game', ensure_message=True)
        games[message.id] = ffi.new("struct GameState *")
        await handle_output(message)
