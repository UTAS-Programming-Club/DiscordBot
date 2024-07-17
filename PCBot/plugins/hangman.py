"""This module contains the bot's hangman minigame command."""

# TODO: Support multiplayer where one player provides the word and the other plays the game
# TODO: Show hanging man to the right of the game instead of the left?

import crescent
import hikari
import linecache
import random
import string
from crescent.ext import docstrings
from colorama import Fore, Style
from typing import Optional

plugin = crescent.Plugin[hikari.GatewayBot, None]()

max_mistake_count = 5

word_file = 'third_party/wordlist/wordlist-20210729.txt'
word_count: Optional[int] = None


class HangmanGame:
    """Maintain and allow guesses for a hangman game."""

    user_id: hikari.snowflakes.Snowflake
    word: str
    guesses: list[chr]

    def __init__(self, user_id):
        global word_count
        if word_count is None:
            with open(word_file) as f:
                word_count = len(f.readlines())

        self.user_id = user_id
        self.guesses = []

        line_num = random.randrange(word_count)
        self.word = linecache.getline(word_file, line_num)
        if '' == self.word:
            raise Exception('Failed to load random word')
        self.word = self.word.translate(str.maketrans('', '', '"\n'))

    def add_guess(self, guess: chr) -> bool:
        """Add a guess if it was not already made, reports whether it was added."""
        if guess not in self.guesses:
            self.guesses.append(guess)
            return True
        else:
            return False

    def get_current_status(
        self, message_id: Optional[hikari.snowflakes.Snowflake]
    ) -> str:
        """Produce a string to describe the current state of the game."""
        mistake_count = len([
          letter for letter in self.guesses if letter not in self.word
        ])

        # Line 1: "Hangman: "
        status = '```ansi\nHangman: \n'

        # Line 2: "╭────╮   Word: _____"
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

        # Line 3: "│    😟"
        if mistake_count >= 1:
            status += '│   '
        if player_won and 0 < mistake_count < max_mistake_count:
            status += ' 😌'
        else if mistake_count >= max_mistake_count - 3:
            status += ' 😟'
        status += '\n'

        # Line 4: "│   ╱│╲  Guesses: ...., N wrong"
        if mistake_count >= 1:
            status += '│   '
        if mistake_count >= max_mistake_count - 2:
            status += '╱│╲  '
        elif mistake_count >= 1:
            status += ' ' * len('╱│╲  ')

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

        # Line 5: "│    │"
        if mistake_count >= 1:
          status += '│'
        if mistake_count >= max_mistake_count - 1:
          status += '    │'
        status += '\n'

        # Line 6: "│   ╱ ╲  RESULT STRING 1"
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
            if message_id is not None:
                games.pop(message_id)

        # Line 7: "┴        RESULT STRING 2"
        if mistake_count >= 1:
            status += '\n┴'
        if mistake_count >= max_mistake_count:
            status += "        The answer was: '" + self.word + "'."

        return status + '```'


games: dict[hikari.snowflakes.Snowflake, HangmanGame] = {}


@plugin.include
@crescent.event
async def on_message_create(event: hikari.MessageCreateEvent):
    """Handle replies to hangman messages containing letter guesses."""
    if event.message.referenced_message is None:
        return
    referenced_message = event.message.referenced_message

    if referenced_message.id not in games:
        return
    game_info = games[referenced_message.id]

    if event.message.author.id != game_info.user_id:
        return

    if event.message.content is None:
        return
    message_text = event.message.content

    if len(event.message.content) != 1:
        return
    message_char = message_text.casefold().replace(' ', '')[0]

    if message_char not in string.ascii_lowercase:
        return

    # TODO: Check if ephmeral replies can even work, switch to a new message?
    if not game_info.add_guess(message_char):
        await event.message.respond(
            "Your guess '" + message_char + "' has already been made.",
            flags=hikari.MessageFlag.EPHEMERAL
        )

    await referenced_message.edit(
      game_info.get_current_status(referenced_message.id)
    )
    await event.message.delete()


@plugin.include
@docstrings.parse_doc
@crescent.command(name='hangman')
class HangmanCommand:
    """
    Play a game of hangman.

    Requested by Clips(clippeh).
    Implemented by something sensible(somethingsensible).
    """

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle hangman command being run by showing the board."""
        game = HangmanGame(ctx.user.id)

        message = await ctx.respond(
          game.get_current_status(None),
          ensure_message=True
        )

        games[message.id] = game
