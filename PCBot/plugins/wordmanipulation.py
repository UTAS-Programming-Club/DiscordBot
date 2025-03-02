"""This module contains the bot's word manipulation minigame command."""

from crescent import AutocompleteContext, command, Context, option, Plugin
from crescent.ext import docstrings
from enum import Enum
from hikari import (
  AutocompleteInteractionOption, GatewayBot, Message, Snowflake
)
from logging import getLogger
from random import choice, sample
from string import ascii_lowercase
from typing import Optional
from PCBot.plugins.replyhandler import (
  GuessOutcome, remove_game, send_text_message, TextGuessGame
)

logger = getLogger(__name__)
plugin = Plugin[GatewayBot, None]()

word_file = 'data/wordlist.txt'
all_words: Optional[list[str]] = None
vowel_words: Optional[list[str]] = None
vowel_set: set[chr] = set("aeiou")


class Minigame(Enum):
    """List of minigames available to play."""

    MissingVowels = "Missing Vowels"
    Unscramble = "Unscramble"


async def minigame_autocomplete(
  ctx: AutocompleteContext,
  option: AutocompleteInteractionOption
) -> list[tuple[str, str]]:
    """Generate a list of commands for option autocomplete."""
    return [(mg.value, mg.name) for mg in Minigame]


class WordManipulationGame(TextGuessGame):
    """Maintain and allow guesses for a word manipulation game."""

    user_id: Optional[Snowflake] = None
    message: Optional[Message] = None
    multiguesser: bool = False
    in_thread: bool = False

    word: str
    manipulated_word: str
    guesses: list[str]
    minigame: Minigame

    def __init__(
      self, user_id: Snowflake, multiguesser: bool, minigame: Minigame
    ):
        """Start a word manipulation game by randomly choosing a word."""
        global all_words, vowel_words
        if all_words is None or vowel_words is None:
            with open(word_file) as f:
                all_words = [line.strip() for line in f]
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
                self.manipulated_word = self._remove_vowels(self.word)
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

    def add_guess(self, guess: str) -> GuessOutcome:
        """Add a guess if it was not already made and reports any issues."""
        processed_guess: str = guess.strip().casefold()

        if set(processed_guess) - set(ascii_lowercase) != set():
            return GuessOutcome.Invalid

        if processed_guess in self.guesses:
            return GuessOutcome.AlreadyMade

        self.guesses.append(processed_guess)
        return GuessOutcome.Valid

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
        status += 'Play by '
        if self.in_thread:
            status += 'sending a'
        else:
            status += 'replying to this'
        status += 'message with a word guess.\n'

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
            remove_game(self.message.id)
            remove_game(self.message.channel_id)

        return status + '```'


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

    multiguesser = option(bool, 'Allow anyone to guess', default=False)
    thread = option(bool, 'Automatically create a thread', default=False)

    async def callback(self, ctx: Context) -> None:
        """Handle word manipulation command being run by starting the minigame."""
        minigame = Minigame[self.minigame]
        game = WordManipulationGame(ctx.user.id, self.multiguesser, minigame)
        await send_text_message(ctx, self.thread, 'Words', game)
