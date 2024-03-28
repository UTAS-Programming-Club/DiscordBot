"""This module contains the bot's rock paper scissors minigame command."""

from __future__ import annotations

import crescent
import hikari
import miru
import random
from crescent.ext import docstrings
from PCBot.botdata import BotData
from typing import Awaitable, Callable

# TODO: Support grid sizes larger than 9x9, limited by reply input method
# TODO: Readd reply input method
# TODO: Add sections 2(column selection) and 3(row selection) of view
# TODO: Replace tile_emojis with an Enum
# TODO: Add grid row and column labels
# TODO: Indicate that bomb count is capped at grid size * grid size
# TODO: Only generate bombs after first prediction,
#       then max box count is one lower

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()
tile_emojis = ['\N{LARGE YELLOW SQUARE}', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '\N{LARGE GREEN SQUARE}', '💥', '🚩']
grids: dict[hikari.snowflakes.Snowflake, Grid] = {}


class Tile:
    """Class to store information about each tile."""

    tile_id = 0
    uncovered = False
    flagged = False


class Grid():
    """Class to store information about the grid."""

    grid_size: int
    bomb_count: int
    grid: list[list[Tile]]

    def __init__(self, grid_size: int, bomb_count: int) -> None:
        """Generate empty grid."""
        self.grid_size = grid_size
        self.bomb_count = bomb_count

        self.grid = [
            [Tile(0) for i in range(self.grid_size)]
            for j in range(self.grid_size)
        ]

    def setup_bombs(self) -> None:
        """Randomly scatters bombs in the self.grid."""
        for bomb in range(self.bomb_count):
            x = (int)(random.random() * self.grid_size)
            y = (int)(random.random() * self.grid_size)
            if(self.grid[x][y].tile_id != 10):
                self.grid[x][y].tile_id = 10
            else:
                while(self.grid[x][y].tile_id == 10):
                    x = (int)(random.random() * self.grid_size)
                    y = (int)(random.random() * self.grid_size)
                self.grid[x][y].tile_id = 10
            # this is ugly I'm just lazy and couldn't think of a better way but it porbably works
            x_upper = (bool)(x-1 > -1)
            x_lower = (bool)(x+1 < self.grid_size)
            y_upper = (bool)(y-1 > -1)
            y_lower = (bool)(y+1 < self.grid_size)

            if(x_upper):
                if(self.grid[x-1][y].tile_id < 8):
                    self.grid[x-1][y].tile_id += 1
                if(y_upper):
                    if(self.grid[x-1][y-1].tile_id < 8):
                        self.grid[x-1][y-1].tile_id += 1
                if(y_lower):
                    if(self.grid[x-1][y+1].tile_id < 8):
                        self.grid[x-1][y+1].tile_id += 1
            if(x_lower):
                if(self.grid[x+1][y].tile_id < 8):
                    self.grid[x+1][y].tile_id += 1
                if(y_upper):
                    if(self.grid[x+1][y-1].tile_id < 8):
                        self.grid[x+1][y-1].tile_id += 1
                if(y_lower):
                    if(self.grid[x+1][y+1].tile_id < 8):
                        self.grid[x+1][y+1].tile_id += 1

            if(y_upper):
                if(self.grid[x][y-1].tile_id < 8):
                    self.grid[x][y-1].tile_id += 1

            if(y_lower):
                if(self.grid[x][y+1].tile_id < 8):
                    self.grid[x][y+1].tile_id += 1

    def __str__(self) -> str:
        """Convert a self.grid into a string."""
        grid_message = ''

        for i in range(self.grid_size):
            grid_message += '\n'
            for j in range(self.grid_size):
                # add tile_emojis[tile.tile_id] to string
                if self.grid[i][j].flagged:
                    grid_message += f'{tile_emojis[11]}'
                elif not self.grid[i][j].uncovered:
                    grid_message += f'{tile_emojis[9]}'
                else:
                    grid_message += f'{tile_emojis[self.grid[i][j].tile_id]}'
        return grid_message


def create_callback_button(
    label: str | None = None,
    *,
    emoji: hikari.Emoji | str | None = None,
    style: hikari.ButtonStyle = hikari.ButtonStyle.PRIMARY,
    disabled: bool = False,
    custom_id: str | None = None,
    row: int | None = None,
    position: int | None = None,
    autodefer: (
        bool | miru.context.AutodeferOptions | hikari.UndefinedType
    ) = hikari.UNDEFINED,
    callback: Callable[
            [miru.context.ViewContext, miru.Button],
            Awaitable[None]
        ] | None = None
) -> miru.Button:
    """Create a miru Button that has a custom callback function."""
    button = miru.Button(
        label=label, emoji=emoji, style=style, disabled=disabled,
        custom_id=custom_id, row=row, position=position, autodefer=autodefer
    )
    button.callback = lambda ctx: callback(ctx, button)
    return button


class MinesweeperPredictionView(miru.View):
    """Miru view which asks the user for minesweeper cell predictions."""

    flag_button: miru.Button
    reveal_button: miru.Button

    def __init__(self) -> None:
        """Create buttons for all three stages and show stage one."""
        super().__init__()
        self.flag_button = create_callback_button(
            '(Un)flag',
            callback=self.prediction_type_button_callback
        )
        self.reveal_button = create_callback_button(
            'Reveal',
            callback=self.prediction_type_button_callback
        )
        self.show_prediction_type_buttons()

    def show_prediction_type_buttons(self) -> None:
        """Remove all buttons and then show stage 1 buttons."""
        self.clear_items()
        self.add_item(self.flag_button)
        self.add_item(self.reveal_button)

    async def prediction_type_button_callback(
        self, ctx: miru.ViewContext, button: miru.Button
    ) -> None:
        """Handle stage 1 buttons being pressed by showing stage 2."""
        if button == self.flag_button:
            await ctx.respond('Pressed flag')
        else:
            await ctx.respond('Pressed reveal')


# def update_cell(col: int, row: int, grid: list[list[Tile]], flag: bool, uncover: bool) -> None:
#     # Row and col must both be in [0, len(grid))
#     if 0 > col >= len(grid) or 0 > row >= len(grid):
#         return
#
#     # Must have exactly one
#     if uncover == flag:
#         return
#
#     # Not allowed to cover or flag if already uncovered
#     if grid[col][row].uncovered:
#         return
#
#     # If uncovering remove flag
#     if uncover:
#         grid[col][row].flagged = False
#         grid[col][row].uncovered = True
#
#     if flag:
#         grid[col][row].flagged = not grid[col][row].flagged

# class SelectionScreen(menu.Screen):
#     """Miru screen which asks the user for a letter or number selection."""
#
#     flag: bool
#     letter: Optional[chr] = None
#
#     def __init__(self, menu: menu.Menu, flag: bool,
#                  self.grid_size: int,
#                  letter: Optional[chr] = None) -> None:
#         """Create an internal screen and store parameters for later use."""
#         super().__init__(menu)
#         self.flag = flag
#         self.letter = letter
#
#     async def build_content(self) -> menu.ScreenContent:
#         """Create a visible screen using stored properties."""
#         prediction_type = '(un)flag' if self.flag else 'reveal'
#         selection_type = 'column' if self.letter is None else 'row'
#         if self.menu.message.id not in grids:
#             return
#         grid = grids[self.menu.message.id].grid
#         return menu.ScreenContent(
#             content=await redraw_grid(grid),
#             embed=hikari.Embed(
#                 title=f'Select {selection_type} for {prediction_type}'
#             ),
#         )
#
#     async def update_reply_prediction(self, reply_prediction: str) -> None:
#         prediction_type = '(un)flag' if self.flag else 'reveal'
#         selection_type = 'column' if self.letter is None else 'row'
#         await self.menu.message.edit(
#             embed=hikari.Embed(
#                 title=f'Select {selection_type} for {prediction_type}',
#                 description=f'Previous prediction was {reply_prediction}'
#             )
#         )
#
#     @menu.button(label='Back', custom_id='back',
#                  style=hikari.ButtonStyle.SECONDARY)
#     async def back(self, ctx: miru.ViewContext,
#                    button: menu.ScreenButton) -> None:
#         """Miru button to restore the previous screen."""
#         await self.menu.pop()
#
#
# class NumberButton(menu.ScreenButton):
#     """Miru screen button that displays a provided number."""
#
#     number: int
#
#     def __init__(self, number: int) -> None:
#         """Create a button with a number label."""
#         self.number = number
#         super().__init__(
#           label=str(number + 1)
#         )
#
#     async def callback(self, ctx: miru.ViewContext) -> None:
#         """Handle user pressing button by showing root with selected cell."""
#         col = ord(self.screen.letter) - ord('A')
#         grid_info = grids[self.menu.message.id]
#         update_cell(col, self.number, grid_info.grid, self.screen.flag, not self.screen.flag)
#         grid_info.prediction_screen.previous_prediction = f'{self.screen.letter}{self.number + 1}'
#         await self.menu.pop_until_root()
#
#
# def create_number_screen(miru_menu: menu.Menu, self.grid_size: int, flag: bool,
#                          letter: chr) -> menu.Screen:
#     """Create a SelectionScreen set up to take a number from the user."""
#     number_screen = SelectionScreen(miru_menu, flag, self.grid_size, letter)
#     back_button = number_screen.get_item_by_id('back')
#     number_screen.remove_item(back_button)
#     for i in range(self.grid_size):
#         number_screen.add_item(NumberButton(i))
#     number_screen.add_item(back_button)
#     return number_screen
#
#
# class LetterButton(menu.ScreenButton):
#     """Miru screen button that displays a provided letter."""
#
#     letter: chr
#
#     def __init__(self, letter_number: int) -> None:
#         """Create a button with a captial letter label."""
#         self.letter = chr(letter_number + ord('A'))
#         super().__init__(
#           label=str(self.letter)
#         )
#
#     async def callback(self, ctx: miru.ViewContext) -> None:
#         """Handle user pressing button by showing number selection screen."""
#         grid = grids[self.menu.message.id].grid
#         number_screen = create_number_screen(self.menu, len(grid), self.screen.flag,
#                                              self.letter)
#         await self.menu.push(number_screen)
#
#
# def create_letter_screen(miru_menu: menu.Menu, self.grid_size: int, flag: bool) -> menu.Screen:
#     """Create a SelectionScreen set up to take a letter from the user."""
#     letter_screen = SelectionScreen(miru_menu, flag, self.grid_size)
#     back_button = letter_screen.get_item_by_id('back')
#     letter_screen.remove_item(back_button)
#     for i in range(self.grid_size):
#         letter_screen.add_item(LetterButton(i))
#     letter_screen.add_item(back_button)
#     return letter_screen
#
#
# class PredictionScreen(menu.Screen):
#     """Miru screen to asks the user what minesweeper prediction to make."""
#
#     previous_prediction: Optional[str] = None
#     self.grid_size: int
#
#     def __init__(self, menu: menu.Menu, self.grid_size: int) -> None:
#         super().__init__(menu)
#         self.grid_size = grid_size
#
#     async def build_content(self) -> menu.ScreenContent:
#         """Create a visible screen to show prediction option buttons."""
#         embed = hikari.Embed(title='Start Prediction')
#         if self.previous_prediction is not None:
#             embed.description =\
#               f'Previous prediction was {self.previous_prediction}'
#         if self.menu.message is not None:
#             grid = grids[self.menu.message.id].grid
#             grid_str = await redraw_grid(grid)
#         else:
#             grid_str = ''
#         return menu.ScreenContent(content=grid_str, embed=embed)
#
#     async def update_reply_prediction(self, reply_prediction: str) -> None:
#         if self.menu.message is None:
#             return
#         self.previous_prediction = reply_prediction
#         await self.menu.message.edit(
#             embed=hikari.Embed(
#                 title='Start Prediction',
#                 description=f'Previous prediction was {self.previous_prediction}'
#             )
#         )
#
#     async def show_initial_grid(self, message: hikari.Message) -> None:
#         """Create a visible screen to show prediction option buttons."""
#         if message.id not in grids:
#             return
#         grid = grids[message.id].grid
#         grid_str = await redraw_grid(grid)
#         await message.edit(grid_str)
#
#     @menu.button(label="(un)Flag")
#     async def flag(self, ctx: miru.ViewContext,
#                    button: menu.ScreenButton) -> None:
#         """Miru button to make a bomb prediction."""
#         await self.menu.push(create_letter_screen(self.menu, self.grid_size, True))
#
#     @menu.button(label="Reveal")
#     async def reveal(self, ctx: miru.ViewContext,
#                        button: menu.ScreenButton) -> None:
#         """Miru button to make a no bomb prediction."""
#         await self.menu.push(create_letter_screen(self.menu, self.grid_size, False))
#
#
# @plugin.include
# @crescent.event
# async def on_grid_message_create(event: hikari.MessageCreateEvent):
#     if event.message.referenced_message is None:
#         return
#     grid_message = event.message.referenced_message
#
#     if grid_message.author == hikari.undefined.UNDEFINED:
#         return
#
#     if grid_message.author.id != plugin.app.get_me().id:
#         return
#
#     if grid_message.id not in grids:
#         return
#     grid_info = grids[grid_message.id]
#     self.grid_size = len(grid_info.grid)
#
#     user_input = list(event.message.content.casefold().replace(' ', ''))
#     print(user_input)
#
#     flag = len(user_input) == 3 and user_input[2] == 'f'
#     if flag:
#         user_input.pop()
#
#     if(len(user_input) == 2):
#         if user_input[0] < 'a' or user_input[0] > 'z':
#             return
#         col_move = ord(user_input[0]) - ord('a')
#
#         # TODO: check if user input is an int then convert it to int
#         if user_input[1] < "0" or user_input[1] > str(self.grid_size - 1):
#             return
#         row_move = user_input[1]
#     else:
#         await event.message.respond("That isn't a valid move!")
#         return
#
#
#     update_cell(col_move, int(row_move), grid_info.grid, flag, not flag)
#     letter = chr(col_move + ord('A'))
#     await grid_info.menu.current_screen.update_reply_prediction(f'{letter}{row_move}')
#     grid_str = await redraw_grid(grid_info.grid)
#     await grid_message.edit(grid_str)
#
#     await event.message.delete()


@plugin.include
@docstrings.parse_doc
@crescent.command(name='minesweeper', dm_enabled=False)
class MineSweeperCommand:
    """
    Play Minesweeper.

    Requested by Camtas(camtas).
    Implemented by something sensible(somethingsensible) &
                   Camtas(camtas).

    Args:
        selected_grid_size: size of grid
        selected_bomb_num: number of bombs in game
    """

    selected_grid_size = crescent.option(
        int, min_value=2, default=9, max_value=9
    )
    selected_bomb_num = crescent.option(
        int, min_value=1, default=5, max_value=80
    )

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle rpschallenge command being run by showing button view."""
        grid = Grid(self.selected_grid_size, self.selected_bomb_num)
        grid.setup_bombs()

        view = MinesweeperPredictionView()
        message = await ctx.respond(grid, components=view, ensure_message=True)
        plugin.model.miru.start_view(view)

        grids[message.id] = grid
