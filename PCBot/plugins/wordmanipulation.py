"""This module contains the bot's word manipulation minigame command."""

from crescent import (
  AutocompleteContext, command, Context, event, option, Plugin
)
from crescent.ext import docstrings
from enum import Enum
from hikari import (
  AutocompleteInteractionOption, ChannelType, GatewayBot, GuildThreadChannel,
  Message, MessageCreateEvent, MessageFlag, PartialMessage
)
from hikari.snowflakes import Snowflake
from logging import getLogger
from random import choice, sample
from string import ascii_lowercase
from typing import Optional

logger = getLogger(__name__)
plugin = Plugin[GatewayBot, None]()

word_file = 'third_party/wordlist/wordlist-20210729.txt'
all_words: Optional[list[str]] = None
vowel_words: Optional[list[str]] = None
vowel_set: set[chr] = set("aeiou")


class Minigame(Enum):
    MissingVowels = "Missing Vowels"
    Unscramble = "Unscramble"


async def minigame_autocomplete(
  ctx: AutocompleteContext,
  option: AutocompleteInteractionOption
) -> list[tuple[str, str]]:
    """Generate a list of commands for option autocomplete."""
    return [(mg.value, mg.name) for mg in Minigame]


class WordManipulationGame:
    """Maintain and allow guesses for a word manipulation game."""

    user_id: Snowflake
    thread_id: Optional[Snowflake] = None
    message: Optional[Message] = None

    word: str
    manipulated_word: str
    guesses: list[str]
    minigame: Minigame
    multiguesser: bool

    def __init__(
      self, user_id: Snowflake, minigame: Minigame, multiguesser: bool
    ):
        """Start a word manipulation game by randomly choosing a word."""
        global all_words, vowel_words
        if all_words is None or vowel_words is None:
            with open(word_file) as f:
                all_words = [line.translate(str.maketrans('', '', '"\n'))
                             for line in f]
                # TODO: Use other _count_vowels results for difficulties
                vowel_words = [
                  word for word in all_words if self._count_vowels(word) == 4
                ]

        self.user_id = user_id
        self.guesses = []
        self.minigame = minigame
        self.multiguesser = multiguesser

        match self.minigame:
            case Minigame.MissingVowels:
                self.word = choice(vowel_words)
                self.manipulated_word =  self._remove_vowels(self.word)
            case Minigame.Unscramble:
                self.word = choice(all_words)
                self.manipulated_word = "".join(
                  sample(self.word, k=len(self.word))
                )

        self.word = self.word.strip()
        logger.info('Starting game with ' + str(self.word))

    def _count_vowels(self, word: str) -> int:
        return sum(map(word.count, vowel_set))

    def _remove_vowels(self, text: str) -> str:
        for char in vowel_set:
            if char in text:
                text = text.replace(char, "?")
        return text

    def add_guess(self, guess: str) -> bool:
        """Add a guess if it was not already made, reports whether it was added."""
        if guess not in self.guesses:
            self.guesses.append(guess)
            return True

        return False

    def _get_guess_info(self, guess: str) -> str:
        info: str = ''

        correct_letter_count: int = 0
        for (guess_digit, number_digit) in zip(guess, self.word):
            if guess_digit != number_digit:
                continue

            correct_letter_count += 1

        if correct_letter_count == 0:
            info += 'No'
        else:
            info += str(correct_letter_count)

        info += ' correct letter'
        if correct_letter_count != 1:
            info += 's'

        return info

    def __str__(self) -> str:
        """Produce a string to describe the current state of the game."""

        # Line 1
        status = 'You are playing word manipulation.\n'

        # Line 2
        match self.minigame:
            case Minigame.MissingVowels:
                status += 'Missing vowels word: '
            case Minigame.Unscramble:
                status += 'Scrambled word: '
        status += self.manipulated_word + '\n'

        # Line 3
        if self.thread_id and self.thread_id in games:
            status += 'Play by sending a message with a word guess.'
        else:
            status += 'Play by replying to this message with a word guess.'
        status += '\n'

        if len(self.guesses) == 0:
            return status

        # Line 4
        status += '\n'

        # Line 5
        status += 'Guesses:```'

        for guess in self.guesses:
            status += '\n' + guess + ': ' + self._get_guess_info(guess)

        if self.word == self.guesses[-1]:
            status += '\n\nYou win!'
            games.pop(self.message.id, None)
            games.pop(self.message.channel_id, None)

        return status + '```'


games: dict[Snowflake, WordManipulationGame] = {}


@plugin.include
@event
async def on_message_create(event: MessageCreateEvent):
    """Handle replies to word manipulation messages containing guesses."""
    game_message: PartialMessage
    if event.message.referenced_message is not None:
        game_message = event.message.referenced_message
    elif event.channel_id in games:
        game_message = games[event.channel_id].message
    else:
        return

    if not game_message or game_message.id not in games:
        return
    game_info: WordManipulationGame = games[game_message.id]

    if (not game_info.multiguesser
          and event.message.author.id != game_info.user_id):
        return

    if event.message.content is None:
        return
    message_text: str = event.message.content.strip().casefold()

    if set(message_text) - set(ascii_lowercase) != set():
        return

    # TODO: Check if ephmeral replies can even work, switch to a new message?
    if not game_info.add_guess(message_text):
        await event.message.respond(
            f'Your guess {message_text} has already been made.',
            flags=MessageFlag.EPHEMERAL
        )

    await game_message.edit(str(game_info))
    await event.message.delete()


@plugin.include
@docstrings.parse_doc
@command(name='words')
class WordManipulationCommand:
    """
    Play a word manipulation minigame.

    Requested by Cam(camtas) & something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    minigame = option(str, 'Which word manipulation minigame to start',
                      autocomplete=minigame_autocomplete)

    multiguesser = option(
      bool, 'Allow anyone to guess', default=False
    )

    thread = option(
      bool, 'Automatically create a thread', default=False
    )

    async def callback(self, ctx: Context) -> None:
        """Handle word manipulation command being run by starting the minigame."""
        minigame = Minigame[self.minigame]
        game = WordManipulationGame(ctx.user.id, minigame, self.multiguesser)

        thread: Optional[GuildThreadChannel] = (
          ctx.app.cache.get_thread(ctx.channel_id)
        )
        if thread is None:
            thread = await ctx.app.rest.fetch_channel(ctx.channel_id)
        in_thread: bool = (
          thread is not None and thread.type is ChannelType.GUILD_PUBLIC_THREAD
          and thread.name == 'Words'
        )

        if not in_thread and self.thread:
            # TODO: Avoid this message
            await ctx.respond(
              'Starting word manipulation game in thread!', ephemeral=True
            )

            thread = await ctx.app.rest.create_thread(
              ctx.channel_id, ChannelType.GUILD_PUBLIC_THREAD, 'Words'
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
