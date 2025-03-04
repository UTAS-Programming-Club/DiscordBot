"""This module contains the bot's hangman minigame command."""

# TODO: Support multiplayer where one player provides the word and the other plays the game
# TODO: Support versus multiplayer where two people privately play the same game and get scored based on time to win/lose
# TODO: Allow guessing entire words and end game either way

from crescent import command, Context, option, Plugin
from crescent.ext import docstrings
from colorama import Fore, Style
from hikari import GatewayBot, Message, Snowflake
from linecache import getline
from logging import getLogger, Logger
from random import randrange
from string import ascii_lowercase
from typing import Optional
from PCBot.plugins.replyhandler import (
  GuessOutcome, remove_game, send_text_message, TextGuessGame
)

logger: Logger = getLogger(__name__)
plugin = Plugin[GatewayBot, None]()

max_mistake_count = 5

word_file = 'data/wordlist.txt'
word_count: Optional[int] = None


class HangmanGame(TextGuessGame):
    """Maintain and allow guesses for a hangman game."""

    message: Optional[Message] = None
    in_thread: bool = False

    word: str
    guesses: list[str]

    def __init__(self, user_id: Snowflake, multiguesser: bool):
        """Start a hangman mode by randomly choosing a word."""
        super().__init__(user_id, multiguesser)

        global word_count
        if word_count is None:
            with open(word_file) as f:
                word_count = len(f.readlines())

        self.guesses = []

        line_num = randrange(word_count)
        self.word = getline(word_file, line_num)
        if '' == self.word:
            raise Exception('Failed to load random word')

        self.word = self.word.strip()
        logger.info('Starting game with ' + str(self.word))

    def add_guess(self, guess: str) -> GuessOutcome:
        """Add a guess if it was not already made and reports any issues."""
        if self.message is None or len(guess) != 1:
            return GuessOutcome.Invalid
        processed_guess = guess.casefold().replace(' ', '')[0]

        if processed_guess not in ascii_lowercase:
            return GuessOutcome.Invalid

        if processed_guess in self.guesses:
            return GuessOutcome.AlreadyMade

        self.guesses.append(processed_guess)
        return GuessOutcome.Valid

    def __str__(self) -> str:
        """Produce a string to describe the current state of the game."""
        if self.message is None:
            return ''

        mistake_count = len([
          letter for letter in self.guesses if letter not in self.word
        ])

        # Line 1
        status = 'You are playing hangman.\n'

        # Line 2
        status += 'Play by '
        if self.in_thread:
            status += 'sending a'
        else:
            status += 'replying to this'
        status += 'message with a letter guess.\n'

        # Line 3:
        status += '```ansi\n'

        # Line 4: "╭────╮   Word: _____"
        if mistake_count >= 1:
            status += '╭────╮   '
        status += 'Word: '

        player_won = True
        for letter in self.word:
            if letter in self.guesses:
                status += letter
            else:
                status += '_'
                player_won = False
        status += '\n'

        # Line 5: "│    😟"
        if mistake_count >= 1:
            status += '│   '
        if player_won and 0 < mistake_count < max_mistake_count:
            status += ' 😌'
        elif mistake_count >= max_mistake_count - 3:
            status += ' 😟'
        status += '\n'

        # Line 6: "│   ╱│╲  Guesses: ...., N wrong"
        if mistake_count >= 1:
            status += '│   '
        if mistake_count >= max_mistake_count - 2:
            status += '╱│╲  '
        elif mistake_count >= 1:
            status += ' ' * len('╱│╲  ')

        if len(self.guesses) != 0:
            status += 'Guesses: ' + Style.BRIGHT
            for guess in self.guesses:
                if guess in self.word:
                    status += Fore.GREEN
                else:
                    status += Fore.RED
                status += guess
            status += Style.RESET_ALL

        if mistake_count >= 1:
            status += f', {mistake_count} wrong'
        status += '\n'

        # Line 6: "│    │"
        if mistake_count >= 1:
            status += '│'
        if mistake_count >= max_mistake_count - 1:
            status += '    │'
        status += '\n'

        # Line 7: "│   ╱ ╲  RESULT STRING 1"
        if mistake_count >= 1:
            status += '│   '
        if mistake_count >= max_mistake_count:
            status += '╱ ╲  '
        elif mistake_count >= 1:
            status += ' ' * len('╱ ╲  ')

        if mistake_count >= max_mistake_count:
            status += 'You have made too many incorrect guesses'
            player_won = False

        if player_won:
            status += 'You have won the game!'

        # Line 8: "┴        RESULT STRING 2"
        if mistake_count >= 1:
            status += '\n┴'
        if mistake_count >= max_mistake_count:
            status += f'        The answer was: {self.word}.'

        if player_won or mistake_count >= max_mistake_count:
            remove_game(self.message.id)
            remove_game(self.message.channel_id)

        return status + '```'


@plugin.include
@docstrings.parse_doc
@command(name='hangman')
class HangmanCommand:
    """
    Play a game of Hangman.

    Requested by Oliver(clippeh).
    Implemented by Joshua(somethingsensible).
    """

    multiguesser = option(bool, 'Allow anyone to guess', default=False)
    thread = option(bool, 'Automatically create a thread', default=False)

    async def callback(self, ctx: Context) -> None:
        """Handle hangman command being run by showing the board."""
        game = HangmanGame(ctx.user.id, self.multiguesser)
        await send_text_message(ctx, self.thread, 'Hangman', game)
