"""This module contains the bot's rock paper scissors minigame command."""

import crescent
import hikari
import miru
from crescent.ext import docstrings
from enum import Enum
from PCBot.botdata import BotData
from typing import Optional

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()

class Tile:
    """Enum to store each user's rock paper scissors selection."""
    
    tileID = 0
    uncovered = False
    
    def __init__(self, tileID):
        self.tileID = tileID


tile_emojis = ['\N{BOMB}']


class MineSweeperView(miru.View):
    """Miri view with buttons to obtain each user's selection."""
    
    grid_size: int
    
    def __init__(self, grid_size: int) -> None:
        self.grid_size = grid_size
        grid = [ [0]*grid_size for i in range(grid_size)]
    
    message = '1 2 3 4 5 6 7 8 9'
    
    for x in range(1):
        message += '/n'
        for y in range(3):
            # add tile_emojis[tile.tileID] to string
            message += 'h'
            
    async def make_move(self, ctx: miru.ViewContext) -> None:
        self.stop()
        


@plugin.include
@docstrings.parse_doc
@crescent.command(name='minesweeper', dm_enabled=False)
class MineSweeperCommand:
    """
    Play Minesweeper

    Requested by Camtas(camtas).
    Implemented by something sensible(somethingsensible) &
                   Camtas(camtas).

    Args:
        grid_size: size of grid
    """

    grid_size = crescent.option(int, default = 9, min_value=2, max_value=18)


    async def callback(self, ctx: crescent.Context) -> None:
        """Handle rpschallenge command being run by showing button view."""
        view = MineSweeperView(grid_size = self.grid_size)
        await ctx.respond(
          'Minesweeper',
          components=view
        )
        plugin.model.miru.start_view(view)
