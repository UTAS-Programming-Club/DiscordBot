"""This module contains the bot's rock paper scissors minigame command."""

import dataclasses
import crescent
import hikari
import random
import miru
from crescent.ext import docstrings
from PCBot.botdata import BotData
from miru.ext import menu
from typing import Optional

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()

class Tile:
    """Class to store information about each tile"""
    
    tileID = 0
    uncovered = False
    flagged = False
    
    def __init__(self, tileID):
        self.tileID = tileID


@dataclasses.dataclass
class GridInfo:
    grid: list[list[Tile]]
    menu: menu.Menu
    prediction_screen: menu.Screen

tile_emojis = ['\N{LARGE YELLOW SQUARE}', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '\N{LARGE GREEN SQUARE}', '💥', '🚩']
grids: dict[hikari.snowflakes.Snowflake, GridInfo] = {}


def create_grid(grid_size: int) -> list[list[Tile]]:
    grid: list[list[Tile]] = []
    for i in range(grid_size):
        row: list[Tile] = []
        for j in range(grid_size):
                row.append(Tile(0))
        grid.append(row)
    return grid


def setup_grid(bomb_num: int, grid: list[list[Tile]]) -> None:
    """Randomly scatters bombs in the grid."""
    grid_size = len(grid)
    for bomb in range(bomb_num):
        x = (int)(random.random() * grid_size)
        y = (int)(random.random() * grid_size)
        if(grid[x][y].tileID != 10):
            grid[x][y].tileID = 10
        else:
            while(grid[x][y].tileID == 10):
                x = (int)(random.random() * grid_size)
                y = (int)(random.random() * grid_size)
            grid[x][y].tileID = 10
        # this is ugly I'm just lazy and couldn't think of a better way but it porbably works
        xUpper = (bool)(x-1 > -1)
        xLower = (bool)(x+1 < grid_size)
        yUpper = (bool)(y-1 > -1)
        yLower = (bool)(y+1 < grid_size)
        
        if(xUpper):
            if(grid[x-1][y].tileID < 8):
                grid[x-1][y].tileID += 1
            if(yUpper):
                if(grid[x-1][y-1].tileID < 8):
                    grid[x-1][y-1].tileID += 1
            if(yLower):
                if(grid[x-1][y+1].tileID < 8):
                    grid[x-1][y+1].tileID += 1
        if(xLower):
            if(grid[x+1][y].tileID < 8):
                grid[x+1][y].tileID += 1
            if(yUpper):
                if(grid[x+1][y-1].tileID < 8):
                    grid[x+1][y-1].tileID += 1
            if(yLower):
                if(grid[x+1][y+1].tileID < 8):
                    grid[x+1][y+1].tileID += 1
                    
        if(yUpper):
            if(grid[x][y-1].tileID < 8): 
                grid[x][y-1].tileID += 1
        
        if(yLower):
            if(grid[x][y+1].tileID < 8):
                grid[x][y+1].tileID += 1


async def redraw_grid(grid: list[list[Tile]]) -> str:
    """Draws up the board by editing the grid_message."""
    grid_size = len(grid)
    grid_message_spacing = '   '* int(grid_size/2)
    grid_message = f'.{grid_message_spacing}--------------------\n.{grid_message_spacing}    MINESWEEPER\n.{grid_message_spacing}--------------------\n.    '
    
    for h in range(grid_size):
        grid_message += chr(h + ord('A')) + '   '
    
    for i in range(grid_size):
        grid_message += f'\n{i+1}  '
        for j in range(grid_size):
            # add tile_emojis[tile.tileID] to string
            if grid[i][j].flagged:
                grid_message += f'{tile_emojis[11]}'
            elif not grid[i][j].uncovered:
                grid_message += f'{tile_emojis[9]}'
            else:
                grid_message += f'{tile_emojis[grid[i][j].tileID]}'
    return grid_message

# swapped around
def update_cell(row: int, col: int, grid: list[list[Tile]], flag: bool, uncover: bool) -> None:
    # Row and col must both be in [0, len(grid))
    if 0 > col >= len(grid) or 0 > row >= len(grid):
        return

    # Must have exactly one
    if uncover == flag:
        return

    # Not allowed to cover or flag if already uncovered
    if grid[col][row].uncovered:
        return

    # If uncovering remove flag
    if uncover:
        grid[col][row].flagged = False
        grid[col][row].uncovered = True
    
    if flag:
        grid[col][row].flagged = not grid[col][row].flagged

def check_win(grid: list[list[Tile]) -> None:
    grid_size = len(grid)
    bomb_num = 0
    
    for i in range(grid_size):
        for j in range(grid_size):
            if grid[i][j].flagged and grid[i][j].tileID is 10:
                bomb_num += 1
            

class SelectionScreen(menu.Screen):
    """Miru screen which asks the user for a letter or number selction."""

    flag: bool
    letter: Optional[chr] = None

    def __init__(self, menu: menu.Menu, flag: bool,
                 grid_size: int,
                 letter: Optional[chr] = None) -> None:
        """Create an internal screen and store parameters for later use."""
        super().__init__(menu)
        self.flag = flag
        self.letter = letter

    async def build_content(self) -> menu.ScreenContent:
        """Create a visible screen using stored properties."""
        prediction_type = '(un)flag' if self.flag else 'reveal'
        selection_type = 'column' if self.letter is None else 'row'
        if self.menu.message.id not in grids:
            return
        grid = grids[self.menu.message.id].grid
        return menu.ScreenContent(
            content=await redraw_grid(grid),
            embed=hikari.Embed(
                title=f'Select {selection_type} for {prediction_type}'
            ),
        )

    async def update_reply_prediction(self, reply_prediction: str) -> None:
        prediction_type = '(un)flag' if self.flag else 'reveal'
        selection_type = 'column' if self.letter is None else 'row'
        await self.menu.message.edit(
            embed=hikari.Embed(
                title=f'Select {selection_type} for {prediction_type}',
                description=f'Previous prediction was {reply_prediction}'
            )
        )

    @menu.button(label='Back', custom_id='back',
                 style=hikari.ButtonStyle.SECONDARY)
    async def back(self, ctx: miru.ViewContext,
                   button: menu.ScreenButton) -> None:
        """Miru button to restore the previous screen."""
        await self.menu.pop()


class NumberButton(menu.ScreenButton):
    """Miru screen button that displays a provided number."""

    number: int

    def __init__(self, number: int) -> None:
        """Create a button with a number label."""
        self.number = number
        super().__init__(
          label=str(number + 1)
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        """Handle user pressing button by showing root with selected cell."""
        col = ord(self.screen.letter) - ord('A')
        grid_info = grids[self.menu.message.id]
        update_cell(col, self.number, grid_info.grid, self.screen.flag, not self.screen.flag)
        grid_info.prediction_screen.previous_prediction = f'{self.screen.letter}{self.number + 1}'
        await self.menu.pop_until_root()


def create_number_screen(miru_menu: menu.Menu, grid_size: int, flag: bool,
                         letter: chr) -> menu.Screen:
    """Create a SelectionScreen set up to take a number from the user."""
    number_screen = SelectionScreen(miru_menu, flag, grid_size, letter)
    back_button = number_screen.get_item_by_id('back')
    number_screen.remove_item(back_button)
    for i in range(grid_size):
        number_screen.add_item(NumberButton(i))
    number_screen.add_item(back_button)
    return number_screen


class LetterButton(menu.ScreenButton):
    """Miru screen button that displays a provided letter."""

    letter: chr

    def __init__(self, letter_number: int) -> None:
        """Create a button with a captial letter label."""
        self.letter = chr(letter_number + ord('A'))
        super().__init__(
          label=str(self.letter)
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        """Handle user pressing button by showing number selection screen."""
        grid = grids[self.menu.message.id].grid
        number_screen = create_number_screen(self.menu, len(grid), self.screen.flag,
                                             self.letter)
        await self.menu.push(number_screen)


def create_letter_screen(miru_menu: menu.Menu, grid_size: int, flag: bool) -> menu.Screen:
    """Create a SelectionScreen set up to take a letter from the user."""
    letter_screen = SelectionScreen(miru_menu, flag, grid_size)
    back_button = letter_screen.get_item_by_id('back')
    letter_screen.remove_item(back_button)
    for i in range(grid_size):
        letter_screen.add_item(LetterButton(i))
    letter_screen.add_item(back_button)
    return letter_screen


class PredictionScreen(menu.Screen):
    """Miru screen to asks the user what minesweeper prediction to make."""

    previous_prediction: Optional[str] = None
    grid_size: int

    def __init__(self, menu: menu.Menu, grid_size: int) -> None:
        super().__init__(menu)
        self.grid_size = grid_size

    async def build_content(self) -> menu.ScreenContent:
        """Create a visible screen to show prediction option buttons."""
        embed = hikari.Embed(title='Start Prediction')
        if self.previous_prediction is not None:
            embed.description =\
              f'Previous prediction was {self.previous_prediction}'
        if self.menu.message is not None:
            grid = grids[self.menu.message.id].grid
            grid_str = await redraw_grid(grid)
        else:
            grid_str = ''
        return menu.ScreenContent(content=grid_str, embed=embed)
    
    async def update_reply_prediction(self, reply_prediction: str) -> None:
        if self.menu.message is None:
            return
        self.previous_prediction = reply_prediction
        await self.menu.message.edit(
            embed=hikari.Embed(
                title='Start Prediction',
                description=f'Previous prediction was {self.previous_prediction}'
            )
        )
    
    async def show_initial_grid(self, message: hikari.Message) -> None:
        """Create a visible screen to show prediction option buttons."""
        if message.id not in grids:
            return
        grid = grids[message.id].grid
        grid_str = await redraw_grid(grid)
        await message.edit(grid_str)

    @menu.button(label="(un)Flag")
    async def flag(self, ctx: miru.ViewContext,
                   button: menu.ScreenButton) -> None:
        """Miru button to make a bomb prediction."""
        await self.menu.push(create_letter_screen(self.menu, self.grid_size, True))

    @menu.button(label="Reveal")
    async def reveal(self, ctx: miru.ViewContext,
                       button: menu.ScreenButton) -> None:
        """Miru button to make a no bomb prediction."""
        await self.menu.push(create_letter_screen(self.menu, self.grid_size, False))


@plugin.include
@crescent.event
async def on_grid_message_create(event: hikari.MessageCreateEvent):
    if event.message.referenced_message is None:
        return
    grid_message = event.message.referenced_message

    if grid_message.author == hikari.undefined.UNDEFINED:
        return

    if grid_message.author.id != plugin.app.get_me().id:
        return
    
    if grid_message.id not in grids:
        return
    grid_info = grids[grid_message.id]
    grid_size = len(grid_info.grid)

    user_input = list(event.message.content.casefold().replace(' ', ''))
    print(user_input)

    flag = len(user_input) == 3 and user_input[2] == 'f'
    if flag:
        user_input.pop()

    if(len(user_input) == 2):
        if user_input[0] < 'a' or user_input[0] > 'z':
            return
        col_move = ord(user_input[0]) - ord('a')
        
        # TODO: check if user input is an int then convert it to int
        if user_input[1] < "0" or user_input[1] > str(grid_size):
            return
        row_move = user_input[1]
    else:
        await event.message.respond("That isn't a valid move!")
        return

    # wasn't correct
    update_cell(col_move, int(row_move)-1, grid_info.grid, flag, not flag)
    letter = chr(col_move + ord('A'))
    await grid_info.menu.current_screen.update_reply_prediction(f'{letter}{row_move}')
    grid_str = await redraw_grid(grid_info.grid)
    await grid_message.edit(grid_str)
    
    await event.message.delete()


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
    selected_bomb_num = crescent.option(int, default = 8, min_value=1, max_value=80)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle rpschallenge command being run by showing button view."""
        prediction_menu = menu.Menu()
        screen = PredictionScreen(prediction_menu, self.selected_grid_size)
        builder =\
          await prediction_menu.build_response_async(plugin.model.miru, screen)
        message = await ctx.respond_with_builder(builder, ensure_message=True)

        grid = create_grid(self.selected_grid_size)
        setup_grid(self.selected_bomb_num, grid)
        grids[message.id] = GridInfo(grid, prediction_menu, screen)

        await screen.show_initial_grid(message)
        plugin.model.miru.start_view(prediction_menu)
