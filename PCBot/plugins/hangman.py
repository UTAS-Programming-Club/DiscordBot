"""This module contains the bot's hangman minigame command."""

# TODO: Find a good word list with some easy and hard words

import crescent
import hikari
# import miru
import random
import string
from crescent.ext import docstrings
from dataclasses import dataclass
# from enum import Enum
# from PCBot.botdata import BotData
# from typing import Optional

plugin = crescent.Plugin[hikari.GatewayBot, None]()

words = [
    'this', 'is', 'a', 'test',
    'these' 'are', 'some', 'words'
]

maxMistakeCount = 5

@dataclass
class HangmanGame:
    word: str
    guesses: list[chr]

    def GetCurrentStatus(self) -> str:
        status = ''
        
        mistakeCount = len([
          letter for letter in self.guesses if letter not in self.word
        ])
        if mistakeCount >= maxMistakeCount:
            status += (
              'You have made too many incorrect guesses\n' +
              'The answer was: ' + self.word + '.'
            )
        else:
            for letter in self.word:
                if letter in self.guesses:
                    status += letter
                else:
                    status += '_'

        status += '\n\nGuesses: ' + ''.join(self.guesses)
        return status

games: dict[hikari.snowflakes.Snowflake, HangmanGame] = {}

@plugin.include
@docstrings.parse_doc
@crescent.command(name='hangman')
class HangmanCommand:
    """
    Play a game of hangman.

    Requested by Clips(clippeh).
    Implemented by something sensible(somethingsensible).
    """

    public = crescent.option(bool, 'Show response publicly', default=False)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle hangman command being run by showing board."""
        word = random.choice(words)
        game = HangmanGame(word, {})
        
        random.choice(words)
        message = await ctx.respond(
          'Hangman: \n' + game.GetCurrentStatus(),
          ephemeral = not self.public,
          ensure_message=True
        )
        games[message.id] = game
