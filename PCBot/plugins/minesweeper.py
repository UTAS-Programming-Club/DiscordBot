"""This module contains the bot's rock paper scissors minigame command."""

import crescent
import hikari
import miru
from crescent.ext import docstrings
from enum import Enum
from PCBot.botdata import BotData
from typing import Optional

class Tile:
    """Enum to store each user's rock paper scissors selection."""
    
    tileID = 0
    uncovered = false
    
    def __init__(self, tileID):
        self.tileID = tileID


tile_emojis = ['\N{GREEN_SQUARE}', '\N{YELLOW_SQUARE}', '\N{BOMB}']


class MineSweeperView(miru.View):
    """Miri view with buttons to obtain each user's selection."""
    
    


@plugin.include
@docstrings.parse_doc
@crescent.command(name='minesweeper', dm_enabled=False)
class MineSweeperCommand:
    """
    Challenge a user to rock paper scissors.

    Requested by iluka wighton(razer304).
    Implemented by something sensible(somethingsensible) &
                   Camtas(camtas).

    Args:
        user: User to challenge.
    """

    user = crescent.option(hikari.User)
    grid_size = crescent.option(hikari.User)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle rpschallenge command being run by showing button view."""
        view = MineSweeperView()
        view.challenger = ctx.user
        view.challengee = self.user.user
        await ctx.respond(
          'Minesweeper',
          components=view
        )
        plugin.model.miru.start_view(view)
