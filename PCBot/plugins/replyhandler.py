"""This module contains functions used to handle replies to bot messages."""

from abc import ABC, abstractmethod
from abcattrs import Abstract, abstractattrs
from crescent import Context, event, Plugin
from enum import Enum
from hikari import (
  ChannelType, GatewayBot, GuildThreadChannel, Message, MessageCreateEvent,
  MessageFlag, Snowflake, TextableGuildChannel
)
from typing import Optional

# TODO: Is this needed?
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
        """Add a guess if it was not already made and reports any issues."""
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Produce a string to describe the current state of the game."""
        pass


# Cannot assign a value here because the assignment
# would happen every time this module is imported
games: Optional[dict[Snowflake, TextGuessGame]]


def reset_reply_handler() -> None:
    """Reset list of text based games on bot start and reload."""
    global games
    games = {}


def add_game(id: Snowflake, game: TextGuessGame) -> None:
    """Start processing replies for a text based game."""
    if 'games' not in globals():
        reset_reply_handler()
    games[id] = game


def remove_game(id: Snowflake) -> None:
    """Stop processing replies for a text based game."""
    if 'games' not in globals():
        return
    games.pop(id, None)


#TODO: Try ctx.channel
async def get_interaction_channel(ctx: Context, name: str) \
  -> tuple[bool, Optional[TextableGuildChannel]]:
    thread: Optional[TextableGuildChannel] = (
      ctx.app.cache.get_thread(ctx.channel_id)
    )
    if thread is None:
        thread = await ctx.app.rest.fetch_channel(ctx.channel_id)

    in_correct_thread: bool = (
      thread is not None and thread.type is ChannelType.GUILD_PUBLIC_THREAD
      and thread.name == name
    )

    return (in_correct_thread, thread)

async def send_text_message(
  ctx: Context, want_thread: bool, name: str, game: TextGuessGame
) -> None:
    in_correct_thread: bool
    channel: Optional[TextableGuildChannel]
    in_correct_thread, channel = await get_interaction_channel(ctx, game)

    message = str(game)

    # TODO: Report want_thread being ignored if in wrong thread?
    if channel.type is not ChannelType.GUILD_PUBLIC_THREAD and want_thread:
        # TODO: Avoid this message
        lower_name: str = name.casefold()
        await ctx.respond(
          f'Starting {lower_name} game in thread!', ephemeral=True
        )

        thread: GuildThreadChannel = await ctx.app.rest.create_thread(
            ctx.channel_id, ChannelType.GUILD_PUBLIC_THREAD, name
        )
        game.message = await thread.send(message)

        game.in_thread = True
        add_game(thread.id, game)
    else:
        if in_correct_thread:
            game.in_thread = True
            add_game(channel.id, game)

        game.message = await ctx.respond(message, ensure_message=True)

    add_game(game.message.id, game)


@plugin.include
@event
async def on_message_create(event: MessageCreateEvent) -> None:
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
