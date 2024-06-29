"""This module contains the bot's hangman minigame command."""

# TODO: Find a good word list with some easy and hard words
# TODO: Support multiplayer where one player provides the word and the other plays the game
# TODO: Report mistakes, either by a number or with a hanging man

import crescent
import hikari
import random
import string
from crescent.ext import docstrings
from dataclasses import dataclass
from typing import Optional

plugin = crescent.Plugin[hikari.GatewayBot, None]()

words = [
    'this', 'is', 'a', 'test',
    'these', 'are', 'some', 'words'
]

maxMistakeCount = 5

@dataclass
class HangmanGame:
    user_id: hikari.snowflakes.Snowflake
    word: str
    guesses: list[chr]


    def AddGuess(self, guess: chr) -> bool:
        if guess not in self.guesses:
            self.guesses.append(guess)
            return True
        else:
            return False

    def GetCurrentStatus(self, message_id: Optional[hikari.snowflakes.Snowflake]) -> str:
        status = 'Hangman: \n'

        playerWon = True
        for letter in self.word:
            if letter in self.guesses:
                status += letter
            else:
                status += '\\_'
                playerWon = False

        status += '\n\nGuesses: ' + ''.join(self.guesses)

        mistakeCount = len([
          letter for letter in self.guesses if letter not in self.word
        ])
        if mistakeCount >= maxMistakeCount:
            status += (
              '\n\nYou have made too many incorrect guesses\n' +
              "The answer was: '" + self.word + "'."
            )
            playerWon = False

        if playerWon:
            status += '\n\nYou have won the game!'
            if message_id is not None:
                games.pop(message_id)
        return status

games: dict[hikari.snowflakes.Snowflake, HangmanGame] = {}

@plugin.include
@crescent.event
async def on_message_create(event: hikari.MessageCreateEvent):
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

    if not game_info.AddGuess(message_char):
        await event.message.respond(
            "Your guess '" + message_char + "' has already been made.",
            flags = hikari.MessageFlag.EPHEMERAL
        )

    await referenced_message.edit(
      game_info.GetCurrentStatus(referenced_message.id)
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
        word = random.choice(words)
        game = HangmanGame(ctx.user.id, word, [])
        
        message = await ctx.respond(
          game.GetCurrentStatus(None),
          ensure_message=True
        )

        games[message.id] = game
