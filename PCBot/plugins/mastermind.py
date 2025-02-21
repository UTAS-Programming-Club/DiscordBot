"""This module contains the bot's mastermind minigame command."""

#TODO: Add difficulties?:
#      Give number of correct digits in correct places
#      Give number of correct digits in correct places and number of correct digits in incorrect places
#      List correct digits in correct places(intentially unclear if multiple)
#      List correct digits in correct places(intentially unclear if multiple) and correct digits in incorrect places
#      ...

from crescent import command, Context, option, Plugin
from hikari import ChannelType, GatewayBot, Message, MessageCreateEvent, PartialMessage
from hikari.snowflakes import Snowflake
from logging import getLogger
from random import randrange
from typing import Optional

logger = getLogger(__name__)
plugin = Plugin[GatewayBot, None]()

#TODO: Make these a command parameter
digit_count: int = 4
higher_or_lower = False


class MastermindGame:
    """Maintain and allow guesses for a mastermind game."""

    user_id: Snowflake
    thread_id: Optional[Snowflake] = None
    message: Optional[Message] = None

    number: str
    guesses: list[str]
    multiguesser: bool

    def __init__(self, user_id: Snowflake, multiguesser: bool):
        """Start a mastermind game by randomly choosing a number."""
        self.user_id = user_id
        self.guesses = []
        self.multiguesser = multiguesser

        self.number = str(
          randrange(10 ** (digit_count - 1), 10 ** digit_count)
        )
        logger.info("Starting game with " + str(self.number))

    def add_guess(self, guess: str) -> bool:
        """Add a guess if it was not already made, reports whether it was added."""
        if guess not in self.guesses:
            self.guesses.append(guess)
            return True

        return False

    def _get_guess_info_mastermind(self, guess) -> str:
        guess_value = int(guess)
        if guess_value < 10 ** (digit_count - 1):
            return "Too small"
        elif guess_value >= 10 ** digit_count:
            return "Too big"

        info: str = ""

        guess_digits = list(guess)
        number_digits = list(self.number)

        # list wrapping is reqired to avoid zip being lazy
        paired_digits = list(zip(guess_digits, number_digits))
        correct_spot_digit_count: int = 0
        for (guess_digit, number_digit) in paired_digits:
            if guess_digit != number_digit:
                continue

            correct_spot_digit_count += 1
            guess_digits.remove(guess_digit)
            number_digits.remove(number_digit)

        if correct_spot_digit_count == 0:
            info += "No"
        else:
            info += str(correct_spot_digit_count)

        info += " correctly positioned digit"
        if correct_spot_digit_count != 1:
            info += "s"

        incorrect_spot_digit_count: int = 0
        for guess_digit in guess_digits:
            if guess_digit not in number_digits:
                continue

            incorrect_spot_digit_count += 1
            number_digits.remove(guess_digit)

        if incorrect_spot_digit_count != 0:
            info += (" and " + str(incorrect_spot_digit_count) +
              " correct but incorrectly positioned digit")

            if incorrect_spot_digit_count != 1:
                info += "s"


        return info

    def _get_guess_info_higher_or_lower(self, guess) -> str:
        if guess > self.number:
            return "Too big"
        elif guess < self.number:
            return "Too small"
        else:
            return "Correct"

    def _get_guess_info(self, guess) -> str:
        if higher_or_lower:
          return self._get_guess_info_higher_or_lower(guess)
        return self._get_guess_info_mastermind(guess)

    def __str__(self) -> str:
        """Produce a string to describe the current state of the game."""
        status = "A " + str(digit_count) + " digit number has been generated."\
          "\n\nReply to this message to make guesses."

        if len(self.guesses) == 0:
            return status

        status += "\n\nGuesses:```"

        for guess in self.guesses:
            status += "\n" + guess + ": " + self._get_guess_info(guess)

        if self.number == self.guesses[-1]:
            status +="\n\nYou win!"
            games.pop(self.message.id, None)
            games.pop(self.message.channel_id, None)

        return status + "```"


games: dict[Snowflake, MastermindGame] = {}


@plugin.include
@crescent.event
async def on_message_create(event: MessageCreateEvent):
    """Handle replies to mastermind messages containing guesses."""
    game_message: PartialMessage
    if event.message.referenced_message is not None:
        game_message = event.message.referenced_message
    elif event.channel_id in games:
        game_message = games[event.channel_id].message
    else:
        return

    if not game_message or game_message.id not in games:
        return
    game_info: MastermindGame = games[game_message.id]

    if (not game_info.multiguesser
          and event.message.author.id != game_info.user_id):
        return

    if event.message.content is None:
        return
    message_text: str = event.message.content.strip()

    if not message_text.isdecimal():
        return

    # TODO: Check if ephmeral replies can even work, switch to a new message?
    if not game_info.add_guess(message_text):
        await event.message.respond(
            f'Your guess {message_text} has already been made.',
            flags=hikari.MessageFlag.EPHEMERAL
        )

    await game_message.edit(str(game_info))
    await event.message.delete()


@plugin.include
@command(name="mastermind")
class MastermindCommand:
    """
    Start Mastermind minigame.

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
            games[thread.id] = game
            game.thread_id = thread.id

            game.message = await thread.send(str(game))
        else:
            if in_thread:
                games[thread.id] = game
                game.thread_id = thread.id

            game.message = await ctx.respond(str(game), ensure_message=True)

        games[game.message.id] = game
