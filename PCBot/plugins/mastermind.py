"""This module contains the bot's mastermind minigame command."""

# TODO: Add difficulties?:
#      Give number of correct digits in correct places
#      Give number of correct digits in correct places and number of correct digits in incorrect places
#      List correct digits in correct places(intentially unclear if multiple)
#      List correct digits in correct places(intentially unclear if multiple) and correct digits in incorrect places
#      ...

from crescent import command, Context, option, Plugin
from crescent.ext import docstrings
from hikari import ChannelType, GatewayBot, GuildThreadChannel, Message
from hikari.snowflakes import Snowflake
from logging import getLogger
from random import randrange
from typing import Optional
from PCBot.plugins.replyhandler import (
  add_game, GuessOutcome, remove_game, TextGuessGame
)

logger = getLogger(__name__)
plugin = Plugin[GatewayBot, None]()

# TODO: Make these command parameters
digit_count: int = 4
higher_or_lower = False


class MastermindGame(TextGuessGame):
    """Maintain and allow guesses for a mastermind game."""

    user_id: Optional[Snowflake] = None
    in_thread: bool = False
    message: Optional[Message] = None

    number: str
    guesses: list[str]
    multiguesser: bool = False

    def __init__(self, user_id: Snowflake, multiguesser: bool):
        """Start a mastermind game by randomly choosing a number."""
        self.user_id = user_id
        self.guesses = []
        self.multiguesser = multiguesser

        self.number = str(
          randrange(10 ** (digit_count - 1), 10 ** digit_count)
        )
        logger.info('Starting game with ' + str(self.number))

    def add_guess(self, guess: str) -> GuessOutcome:
        """Add a guess if it was not already made, reports whether it was added."""
        processed_guess: str = guess.strip()

        if not processed_guess.isdecimal():
            return GuessOutcome.Invalid

        if processed_guess in self.guesses:
            return GuessOutcome.AlreadyMade

        self.guesses.append(processed_guess)
        return GuessOutcome.Valid

    def _get_guess_info_mastermind(self, guess: str) -> str:
        guess_value = int(guess)
        if guess_value < 10 ** (digit_count - 1):
            return 'Too small'
        elif guess_value >= 10 ** digit_count:
            return 'Too big'

        info: str = ''

        guess_digits = list(guess)
        number_digits = list(self.number)

        # list wrapping is to prevent zip being lazy as the lists are modified
        paired_digits = list(zip(guess_digits, number_digits))
        correct_spot_digit_count: int = 0
        for (guess_digit, number_digit) in paired_digits:
            if guess_digit != number_digit:
                continue

            correct_spot_digit_count += 1
            guess_digits.remove(guess_digit)
            number_digits.remove(number_digit)

        if correct_spot_digit_count == 0:
            info += 'No'
        else:
            info += str(correct_spot_digit_count)

        info += ' correctly positioned digit'
        if correct_spot_digit_count != 1:
            info += 's'

        incorrect_spot_digit_count: int = 0
        for guess_digit in guess_digits:
            if guess_digit not in number_digits:
                continue

            incorrect_spot_digit_count += 1
            number_digits.remove(guess_digit)

        if incorrect_spot_digit_count != 0:
            info += (' and ' + str(incorrect_spot_digit_count) +
              ' correct but incorrectly positioned digit')

            if incorrect_spot_digit_count != 1:
                info += 's'

        return info

    def _get_guess_info_higher_or_lower(self, guess: str) -> str:
        if guess > self.number:
            return 'Too big'
        elif guess < self.number:
            return 'Too small'
        else:
            return 'Correct'

    def _get_guess_info(self, guess: str) -> str:
        if higher_or_lower:
            return self._get_guess_info_higher_or_lower(guess)
        return self._get_guess_info_mastermind(guess)

    def __str__(self) -> str:
        """Produce a string to describe the current state of the game."""
        # Line 1
        status = 'You are playing mastermind.\n'

        # Line 2
        status += (
          'A ' + str(digit_count) + ' digit number has been generated.\n'
        )

        # Line 3
        if self.in_thread:
            status += 'Play by sending a message with a number guess.'
        else:
            status += 'Play by replying to this message with a number guess.'
        status += '\n'

        if len(self.guesses) == 0:
            return status

        # Line 4
        status += '\n'

        # Line 5
        status += 'Guesses:```'

        for guess in self.guesses:
            status += '\n' + guess + ': ' + self._get_guess_info(guess)

        if self.number == self.guesses[-1]:
            status += '\n\nYou win!'
            remove_game(self.message.id)
            remove_game(self.message.channel_id)

        return status + '```'


@plugin.include
@docstrings.parse_doc
@command(name='mastermind')
class MastermindCommand:
    """
    Play a game of Mastermind.

    Requested by Cam(camtas) & something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    multiguesser = option(
      bool, 'Allow anyone to guess', default=False
    )

    thread = option(
      bool, 'Automatically create a thread', default=False
    )

    async def callback(self, ctx: Context) -> None:
        """Handle mastermind command being run by starting the minigame."""
        game = MastermindGame(ctx.user.id, self.multiguesser)

        thread: Optional[GuildThreadChannel] = (
          ctx.app.cache.get_thread(ctx.channel_id)
        )
        if thread is None:
            thread = await ctx.app.rest.fetch_channel(ctx.channel_id)
        in_thread: bool = (
          thread is not None and thread.type is ChannelType.GUILD_PUBLIC_THREAD
          and thread.name == 'Mastermind'
        )

        if not in_thread and self.thread:
            # TODO: Avoid this message
            await ctx.respond(
              'Starting mastermind game in thread!', ephemeral=True
            )

            thread = await ctx.app.rest.create_thread(
              ctx.channel_id, ChannelType.GUILD_PUBLIC_THREAD, 'Mastermind'
            )
            add_game(thread.id, game)
            game.in_thread = True

            game.message = await thread.send(str(game))
        else:
            if in_thread:
                add_game(thread.id, game)
                game.in_thread = True

            game.message = await ctx.respond(str(game), ensure_message=True)

        add_game(game.message.id, game)
