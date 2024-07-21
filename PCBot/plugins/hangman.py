"""This module contains the bot's hangman minigame command."""

# TODO: Support multiplayer where one player provides the word and the other plays the game
# TODO: Support versus multiplayer where two people privately play the same game and get scored based on time to win/lose

import crescent
import hikari
import linecache
import random
import string
from crescent.ext import docstrings
from colorama import Fore, Style
from hikari.channels import ChannelType
from typing import Optional

plugin = crescent.Plugin[hikari.GatewayBot, None]()

max_mistake_count = 5

word_file = 'third_party/wordlist/wordlist-20210729.txt'
word_count: Optional[int] = None


class HangmanGame:
    """Maintain and allow guesses for a hangman game."""

    user_id: hikari.snowflakes.Snowflake
    thread_id: Optional[hikari.snowflakes.Snowflake] = None
    message: Optional[hikari.Message] = None

    word: str
    guesses: list[chr]
    multiguesser: bool

    def __init__(
      self, user_id: hikari.snowflakes.Snowflake, multiguesser: bool
    ):
        """Start a hangman mode by randomly choosing a word from the file."""
        global word_count
        if word_count is None:
            with open(word_file) as f:
                word_count = len(f.readlines())

        self.user_id = user_id
        self.guesses = []
        self.multiguesser = multiguesser

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

    def __str__(self) -> str:
        """Produce a string to describe the current state of the game."""
        mistake_count = len([
          letter for letter in self.guesses if letter not in self.word
        ])

        # Line 1
        status = 'You are playing hangman.\n'

        # Line 2
        global games
        if self.thread_id and self.thread_id in games:
            status += 'Play by sending a message with a letter guess.'
        else:
            status += 'Play by replying to this message with a letter guess.'
        status += '\n```ansi\n'

        # Line 3: "╭────╮   Word: _____"
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

        # Line 4: "│    😟"
        if mistake_count >= 1:
            status += '│   '
        if player_won and 0 < mistake_count < max_mistake_count:
            status += ' 😌'
        elif mistake_count >= max_mistake_count - 3:
            status += ' 😟'
        status += '\n'

        # Line 5: "│   ╱│╲  Guesses: ...., N wrong"
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

        if (self.message is not None and
             (player_won or mistake_count >= max_mistake_count)):
            games.pop(self.message.id)
            games.pop(self.message.channel_id)

        return status + '```'


games: dict[hikari.snowflakes.Snowflake, HangmanGame] = {}


@plugin.include
@crescent.event
async def on_message_create(event: hikari.MessageCreateEvent):
    """Handle replies to hangman messages containing letter guesses."""
    if event.message.referenced_message is not None:
        game_message = event.message.referenced_message
    elif event.channel_id in games:
        game_message = games[event.channel_id].message
    else:
        return

    if not game_message or game_message.id not in games:
        return
    game_info = games[game_message.id]

    if (not game_info.multiguesser
          and event.message.author.id != game_info.user_id):
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
            f'Your guess {message_char} has already been made.',
            flags=hikari.MessageFlag.EPHEMERAL
        )

    await game_message.edit(str(game_info))
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

    multiguesser = crescent.option(
      bool, 'Allow anyone to guess', default=False
    )

    thread = crescent.option(
      bool, 'Automatically create a thread', default=False
    )

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle hangman command being run by showing the board."""
        game = HangmanGame(ctx.user.id, self.multiguesser)

        thread = ctx.app.cache.get_thread(ctx.channel_id)
        if thread is None:
            thread = await ctx.app.rest.fetch_channel(ctx.channel_id)
        in_thread = (
          thread is not None and thread.type is ChannelType.GUILD_PUBLIC_THREAD
          and thread.name == 'Hangman'
        )

        if not in_thread and self.thread:
            # TODO: Avoid this message
            await ctx.respond(
              'Starting hangman game in thread!', ephemeral=True
            )

            thread = await ctx.app.rest.create_thread(
              ctx.channel_id, ChannelType.GUILD_PUBLIC_THREAD, 'Hangman'
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
