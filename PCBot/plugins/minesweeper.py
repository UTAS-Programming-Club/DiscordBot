"""This module contains the bot's minesweeper minigame command."""

from __future__ import annotations

import crescent
import hikari
import inspect
import miru
import random
import string
from crescent.ext import docstrings
from enum import Enum
from PCBot.botdata import BotData
from typing import Awaitable, Callable

# TODO: Support grid sizes larger than 9x9, limited by reply input method
# TODO: Readd reply input method
# TODO: Finish button input method
# TODO: Replace tile_emojis with an Enum
# TODO: Add grid row and column labels
# TODO: Indicate that bomb count is capped at grid size * grid size
# TODO: Only generate bombs after first prediction,
#       then max box count is one lower
# TODO: Add description text
# TODO: Add last input method to description
# TODO: Fix delay when changing buttons
# TODO: Lock to single player? Have both single player and cooperative modes?

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()
tile_emojis = ['\N{LARGE YELLOW SQUARE}', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '\N{LARGE GREEN SQUARE}', '💥', '🚩']
grids: dict[hikari.snowflakes.Snowflake, Grid] = {}


class Tile:
    """Class to store information about each tile."""

    tile_id = 0
    uncovered = False
    flagged = False

class State(Enum):
    Ongoing = 0
    Lost = 1
    Won = 2

class Grid:
    """Class to store information about the grid."""
    
    # potential status enum for grid? such as won, lost and ongoing for prediction text updating?
    
    size: int
    bomb_count: int
    grid: list[list[Tile]]
    grid_state: State

    def __init__(self, size: int, bomb_count: int) -> None:
        """Generate empty grid."""
        self.size = size
        self.bomb_count = bomb_count
        self.grid_state = State.Ongoing

        self.grid = [
            [Tile() for i in range(self.size)]
            for j in range(self.size)
        ]
        # here for now but should be moved
        self.setup_bombs()

    def setup_bombs(self) -> None:
        """Randomly scatters bombs in the grid."""
        for bomb in range(self.bomb_count):
            x = (int)(random.random() * self.size)
            y = (int)(random.random() * self.size)
            if(self.grid[x][y].tile_id != 10):
                self.grid[x][y].tile_id = 10
            else:
                while(self.grid[x][y].tile_id == 10):
                    x = (int)(random.random() * self.size)
                    y = (int)(random.random() * self.size)
                self.grid[x][y].tile_id = 10
            # this is ugly I'm just lazy and couldn't think of a better way but it porbably works
            x_upper = (bool)(x-1 > -1)
            x_lower = (bool)(x+1 < self.size)
            y_upper = (bool)(y-1 > -1)
            y_lower = (bool)(y+1 < self.size)

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
        """Convert a grid into a string."""
        grid_message = ''

        for i in range(self.size):
            grid_message += '\n'
            for j in range(self.size):
                # add tile_emojis[tile.tile_id] to string
                if self.grid[i][j].flagged:
                    grid_message += f'{tile_emojis[11]}'
                elif not self.grid[i][j].uncovered:
                    grid_message += f'{tile_emojis[9]}'
                else:
                    grid_message += f'{tile_emojis[self.grid[i][j].tile_id]}'
        return grid_message

    def update_cell(self, row: int, col: int, move_type: PredictionType) -> None:
        """Updates selected cell on the grid"""
        if self.grid_state == State.Lost or self.grid_state == State.Won:
            return
        
        # Row and col must both be in [0, len(grid))
        if 0 > col >= len(self.grid) or 0 > row >= len(self.grid):
            return

        # Not allowed to cover or flag if already uncovered
        if self.grid[col][row].uncovered:
            return

        # If uncovering remove flag
        if move_type is PredictionType.Reveal:
            self.grid[col][row].flagged = False
            self.grid[col][row].uncovered = True
            if self.grid[col][row].tile_id == 10:
                self.grid_state = State.Lost

        if move_type is PredictionType.Flag:
            self.grid[col][row].flagged = not self.grid[col][row].flagged
        
        self.fill_blanks(row, col)
        self.check_win()

    def check_win(self) -> None:
        """Check if a grid is completed"""
        grid_size = len(self.grid)
        bomb_num = 0
        
        for i in range(grid_size):
            for j in range(grid_size):
                if self.grid[i][j].flagged and self.grid[i][j].tile_id == 10:
                    bomb_num += 1
        
        if self.bomb_count == bomb_num:
            self.grid_state = State.Won
            
    def fill_blanks(self, row: int, col: int) -> None:
        if self.grid[col][row].uncovered == False:
            self.grid[col][row].uncovered = True
        else:
            return
        
        if not self.grid[col][row].tile_id == 0:
            return
        
        # this is ugly I'm just lazy and couldn't think of a better way but it porbably works
        x_upper = (bool)(col-1 > -1)
        x_lower = (bool)(col+1 < self.size)
        y_upper = (bool)(row-1 > -1)
        y_lower = (bool)(row+1 < self.size)

        if(x_upper):
            self.fill_blanks(row, col-1)
            
            if(y_upper):
                self.fill_blanks(row-1, col-1)
            if(y_lower):
                self.fill_blanks(row+1, col-1)
        if(x_lower):
            self.fill_blanks(row, col+1)
            
            if(y_upper):
                self.fill_blanks(row-1, col+1)
            if(y_lower):
                self.fill_blanks(row+1, col+1)

        if(y_upper):
            self.fill_blanks(row-1, col)

        if(y_lower):
            self.fill_blanks(row+1, col)

class PredictionType(Enum):
    """Enum to store the type of prediction the user is making/has made."""

    Flag   = 0,
    Reveal = 1


class PredictionStage(Enum):
    """Enum to store the current prediction stage of the user."""

    Type =   0,
    Column = 1,  # Letter
    Row    = 2   # Number


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


def create_output_text(
    grid: Grid, last_prediction_type: PredictionType | None,
    last_column: int | None, last_row: int | None
) -> str:
    """Produce a string that includes the grid, input methods and last move."""
    if (
         last_prediction_type is not None and
         last_column is not None and last_row is not None
    ):
        if grid.grid_state is State.Won:
            return inspect.cleandoc('''You are playing minesweeper.
            This game is complete! Please use /minesweeper to start again.'''
            ) + str(grid)
        elif grid.grid_state is State.Lost:
            return inspect.cleandoc('''You are playing minesweeper.
            This game is over! Please use /minesweeper to start again.'''
            ) + str(grid)
    
        if last_prediction_type is PredictionType.Flag:
            prediction_str = '(un)flag'
        elif last_prediction_type is PredictionType.Reveal:
            prediction_str = 'reveal'
        column_str = string.ascii_uppercase[last_column]
        row_str = str(last_row + 1)
        return inspect.cleandoc(f'''You are playing minesweeper.
        Play using either the buttons below or by replying to this message
        with a message like C7 or C 7.
        The last move to was to {prediction_str} cell {column_str}{row_str}.'''
        ) + str(grid)
    else:
        return inspect.cleandoc('''You are playing minesweeper.
        Play using either the buttons below or by replying to this message
        with a message like C7 or C 7.'''
        ) + str(grid)


class MinesweeperPredictionView(miru.View):
    """Miru view which asks the user for minesweeper cell predictions."""

    grid: Grid
    flag_button: miru.Button
    reveal_button: miru.Button
    back_button: miru.Button
    selection_buttons: list[miru.Button]

    current_stage: PredictionStage
    current_type: PredictionType | None = None
    current_column: int | None = None
    current_row: int | None = None

    def __init__(self, grid: Grid) -> None:
        """Create buttons for all three stages and show stage one."""
        super().__init__()
        self.grid = grid
        self.flag_button = create_callback_button(
            '(Un)flag',
            callback=self.prediction_type_button_callback
        )
        self.reveal_button = create_callback_button(
            'Reveal',
            callback=self.prediction_type_button_callback
        )
        self.reveal_button = create_callback_button(
            'Reveal',
            callback=self.prediction_type_button_callback
        )
        self.back_button = create_callback_button(
            'Back',
            style=hikari.ButtonStyle.DANGER,
            callback=self.back_button_callback
        )
        self.selection_buttons = [
            create_callback_button(
                '',
                callback=self.selection_button_callback
            )
            for i in range(grid.size)
        ]
        self.current_stage = PredictionStage.Type
        # Cannot use show_prediction_type_buttons as it requires async
        self.add_item(self.flag_button)
        self.add_item(self.reveal_button)

    async def show_prediction_type_buttons(self) -> None:
        """Remove all buttons and then show stage 1 buttons."""
        if self.current_stage is not PredictionStage.Type:
            raise Exception('Invalid prediction stage for type buttons')
        self.clear_items()
        self.add_item(self.flag_button)
        self.add_item(self.reveal_button)
        self.grid.update_cell(self.current_column, self.current_row, self.current_type)
        grid_str = create_output_text(
            self.grid, self.current_type, self.current_column, self.current_row
        )
        await self.message.edit(grid_str, components=self)

    async def show_selection_buttons(self) -> None:
        """Remove all buttons and then show stage 2 or 3 buttons."""
        if self.current_stage not in [
            PredictionStage.Column, PredictionStage.Row
        ]:
            raise Exception('Invalid prediction stage for selection buttons')
        self.clear_items()
        for idx, selection_button in enumerate(self.selection_buttons):
            if self.current_stage is PredictionStage.Column:
                selection_button.label = string.ascii_uppercase[idx]
            else:
                selection_button.label = str(idx + 1)
            self.add_item(selection_button)
        self.add_item(self.back_button)
        await self.message.edit(components=self)

    async def prediction_type_button_callback(
        self, ctx: miru.ViewContext, button: miru.Button
    ) -> None:
        """Handle stage 1 buttons being pressed by showing stage 2."""
        if self.current_stage is not PredictionStage.Type:
            raise Exception('Invalid prediction stage for type buttons')
        self.current_stage = PredictionStage.Column
        if button == self.flag_button:
            self.current_type = PredictionType.Flag
        else:
            self.current_type = PredictionType.Reveal
        await self.show_selection_buttons()

    async def back_button_callback(
        self, ctx: miru.ViewContext, button: miru.Button
    ) -> None:
        """Handle back button being pressed by reverting to previous stage."""
        if self.current_stage is PredictionStage.Column:
            self.current_stage = PredictionStage.Type
            await self.show_prediction_type_buttons()
        elif self.current_stage is PredictionStage.Row:
            self.current_stage = PredictionStage.Column
            await self.show_selection_buttons()
        else:
            raise Exception('Invalid prediction stage for back button')

    async def selection_button_callback(
        self, ctx: miru.ViewContext, button: miru.Button
    ) -> None:
        """Handle state 2 and 3 buttons being pressed."""
        if self.current_stage is PredictionStage.Column:
            self.current_stage = PredictionStage.Row
            self.current_column = string.ascii_uppercase.index(button.label)
            await self.show_selection_buttons()
        elif self.current_stage is PredictionStage.Row:
            self.current_stage = PredictionStage.Type
            self.current_row = int(button.label) - 1
            await self.show_prediction_type_buttons()
        else:
            raise Exception('Invalid prediction stage for selection buttons')


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
@crescent.command(name='minesweeper')
class MinesweeperCommand:
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
        """Handle minesweeper command being run by showing grid and buttons."""
        grid = Grid(self.selected_grid_size, self.selected_bomb_num)
        grid.setup_bombs()
        grid_str = create_output_text(grid, None, None, None)

        view = MinesweeperPredictionView(grid)
        message = await ctx.respond(
            grid_str, components=view, ensure_message=True
        )
        plugin.model.miru.start_view(view)

        grids[message.id] = grid
