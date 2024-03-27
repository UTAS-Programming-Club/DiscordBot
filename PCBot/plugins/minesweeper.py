"""This module contains the bot's rock paper scissors minigame command."""

import random
import crescent
import hikari
import miru
from crescent.ext import docstrings
from PCBot.botdata import BotData
from typing import Optional

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()

class Tile:
    """Class to store information about each tile"""
    
    tileID = 0
    uncovered = False
    flagged = False
    
    def __init__(self, tileID):
        self.tileID = tileID


tile_emojis = ['\N{LARGE YELLOW SQUARE}', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '\N{LARGE GREEN SQUARE}', '\N{BOMB}']
grid_message_callbacks = []

class MineSweeperView(miru.View):
    """Miru view with button to draw up grid"""
    
    grid_size: int
    bomb_num: int
    
    grid_message = ''
    grid = None
    
    game_over = False
    
    def __init__(self, grid_size: int, bomb_num) -> None:
        super().__init__()
        self.grid_size = grid_size
        self.bomb_num = bomb_num
        
        self.grid: list[list[Tile]] = []
        for i in range(grid_size):
            row: list[Tile] = []
            for j in range(grid_size):
                    row.append(Tile(0))
            self.grid.append(row)
        
        grid_message_callbacks.append(self.on_grid_message_create)
        self.setup()
        
    def setup(self) -> None:
        """ randomly scatters bombs in the grid """
        for bomb in range(self.bomb_num):
            x = (int)(random.random() * self.grid_size)
            y = (int)(random.random() * self.grid_size)
            if(self.grid[x][y].tileID != 10):
                self.grid[x][y].tileID = 10
            else:
                while(self.grid[x][y].tileID == 10):
                    x = (int)(random.random() * self.grid_size)
                    y = (int)(random.random() * self.grid_size)
                self.grid[x][y].tileID = 10
            # this is ugly I'm just lazy and couldn't think of a better way but it porbably works
            xUpper = (bool)(x-1 > -1)
            xLower = (bool)(x+1 < self.grid_size)
            yUpper = (bool)(y-1 > -1)
            yLower = (bool)(y+1 < self.grid_size)
            
            if(xUpper):
                if(self.grid[x-1][y].tileID < 8):
                    self.grid[x-1][y].tileID += 1
                if(yUpper):
                    if(self.grid[x-1][y-1].tileID < 8):
                        self.grid[x-1][y-1].tileID += 1
                if(yLower):
                    if(self.grid[x-1][y+1].tileID < 8):
                        self.grid[x-1][y+1].tileID += 1
            if(xLower):
                if(self.grid[x+1][y].tileID < 8):
                    self.grid[x+1][y].tileID += 1
                if(yUpper):
                    if(self.grid[x+1][y-1].tileID < 8):
                        self.grid[x+1][y-1].tileID += 1
                if(yLower):
                    if(self.grid[x+1][y+1].tileID < 8):
                        self.grid[x+1][y+1].tileID += 1
                        
            if(yUpper):
                if(self.grid[x][y-1].tileID < 8): 
                    self.grid[x][y-1].tileID += 1
            
            if(yLower):
                if(self.grid[x][y+1].tileID < 8):
                    self.grid[x][y+1].tileID += 1
                    
    def make_move(self, col: int, row: int, flag: bool = False) -> str:
        if(self.game_over == True):
            return
        
        self.grid[col][row].uncovered = True
        if(self.grid[col][row].tileID == 10):
            self.game_over = True
            return 'Game Over!' # feedback for player such as 'revealing x,y'
        else:
            return f'Revealing tile {col}, {row}' # game over message/some kind of response
            
        # simply call redraw except we can't rn
        
    async def redraw_grid(self, ctx: miru.ViewContext) -> None:
        self.grid_message = ''

        """ draws up the board by editing the grid_message """
        for i in range(self.grid_size):
            self.grid_message += '\n'
            for j in range(self.grid_size):
                # add tile_emojis[tile.tileID] to string
                if(self.grid[i][j].uncovered == False):
                    self.grid_message += f'{tile_emojis[9]}'
                else:
                    self.grid_message += f'{tile_emojis[self.grid[i][j].tileID]}'
        await ctx.edit_response(f'{self.grid_message}')
    
    @miru.button(label='Start', emoji=tile_emojis[10],
                 style=hikari.ButtonStyle.PRIMARY)
    async def start_button(self, ctx: miru.ViewContext,
                          button: miru.Button) -> None:
        self.disabled = True
        await self.redraw_grid(ctx)
        
    @miru.button(label='Redraw', emoji=tile_emojis[10],
                 style=hikari.ButtonStyle.PRIMARY)
    async def redraw_button(self, ctx: miru.ViewContext,
                          button: miru.Button) -> None:
        if(self.game_over == True):
            self.disabled = True
        
        await self.redraw_grid(ctx)

    async def on_grid_message_create(self, event: hikari.MessageCreateEvent):
        if self.is_bound == False:
            return
        if (event.message.referenced_message.id != 
            self.message.id):
            return
        user_input = event.message.content.casefold().split()
        
        print(event.message.content)
        print(user_input)
        if(len(user_input) == 2):
            if user_input[0] < 'a' or user_input[0] > 'z':
                await event.message.respond("That isn't a valid move!")
                return
            col_move = ord(user_input[0]) - ord('a')
            
            # TODO: check if user input is an int then convert it to int
            if user_input[1] < "0" or user_input[1] > str(self.grid_size - 1):
                await event.message.respond("That isn't a valid move!")
                return
            row_move = user_input[1]
        elif(len(user_input) == 3):
            await event.message.respond("That isn't a valid move!")
            return
        else:
            await event.message.respond("That isn't a valid move!")
            return

        await event.message.respond(self.make_move(col_move, int(row_move)))

@plugin.include
@crescent.event
async def on_grid_message_create(event: hikari.MessageCreateEvent):
    if event.message.referenced_message is None:
        return
    
    for callback in grid_message_callbacks:
        await callback(event)


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
        selected_grid_size: size of grid
        selected_bomb_num: number of bombs in game
    """

    selected_grid_size = crescent.option(int, default = 9, min_value=2, max_value=18)
    selected_bomb_num = crescent.option(int, default = 5, min_value=1, max_value=80)


    async def callback(self, ctx: crescent.Context) -> None:
        """Handle rpschallenge command being run by showing button view."""
        view = MineSweeperView(grid_size = self.selected_grid_size, bomb_num = self.selected_bomb_num)
        await ctx.respond(
          'Minesweeper',
          components=view
        )
        plugin.model.miru.start_view(view)
