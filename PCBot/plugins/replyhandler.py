"""This module contains functions used to handle replies to bot messages."""

from abc import ABC, abstractmethod
from abcattrs import Abstract, abstractattrs
from crescent import event, Plugin
from collections.abc import Awaitable, Callable
from enum import Enum
from hikari import GatewayBot, Message, MessageCreateEvent, MessageFlag
from hikari.snowflakes import Snowflake
from typing import Optional

plugin = Plugin[GatewayBot, None]()


class GuessOutcome(Enum):
    """List of outcomes of the add_guess function for text based games."""

    Valid       = 1
    Invalid     = 2
    AlreadyMade = 3


@abstractattrs
class TextGuessGame(ABC):
    """Base class for games supporting text based guessing."""

    user_id: Abstract[Optional[Snowflake]]
    message: Abstract[Optional[Message]]
    multiguesser: Abstract[bool]

    @abstractmethod
    def add_guess(self, guess: str) -> GuessOutcome:
        """Add a guess if it was not already made, reports whether it was added."""
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Produce a string to describe the current state of the game."""
        pass


# Cannot assign a value here because the assignment
# would happen every time this module is imported
games: Optional[dict[Snowflake, TextGuessGame]]


def reset_reply_handler():
    """Reset list of text based games on bot start and reload."""
    global games
    games = {}


def add_game(id: Snowflake, game: TextGuessGame):
    """Start processing replies for a text based game."""
    if 'games' not in globals():
        reset_reply_handler()
    games[id] = game


def remove_game(id: Snowflake):
    """Stop processing replies for a text based game."""
    if 'games' not in globals():
        return
    games.pop(id, None)


@plugin.include
@event
async def on_message_create(event: MessageCreateEvent):
    """Pass messages to each registered reply handler."""
    if 'games' not in globals():
        return

    game_message: PartialMessage
    if event.message.referenced_message is not None:
        game_message = event.message.referenced_message
    elif event.channel_id in games:
        game_message = games[event.channel_id].message
    else:
        return

    if not game_message or game_message.id not in games:
        return
    game_info: TextGuessGame = games[game_message.id]

    if (not game_info.multiguesser
          and event.message.author.id != game_info.user_id):
        return

    if event.message.content is None:
        return
    message_text: str = event.message.content

    outcome: GuessOutcome = game_info.add_guess(message_text)
    match outcome:
        case GuessOutcome.AlreadyMade:
            # TODO: Check if ephemeral replies can even work, switch to a new message?
            await event.message.respond(
              f'Your guess {message_text} has already been made.',
              flags=MessageFlag.EPHEMERAL
            )
        case GuessOutcome.Invalid:
            return

    await game_message.edit(str(game_info))
    await event.message.delete()
