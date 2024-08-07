"""This module contains the bot's minesweeper minigame command."""

# TODO: Figure out why some chars stop appearing for 14x14 despite being well
# below the length limit. I tried copying the message and reposting it and hit
# the same issue so it is not bot specific.
# TODO: Add messages that check for and prevent exceptions from occurring
# TODO: Ensure bomb count is capped at grid size * grid_size - 1
# TODO: Switch from bomb to boom char?
# TODO: Add thread support, like hangman
# TODO: Add custom emoji to the bot that is the flag one on top of the green square one
# TODO: Report expiry
# TODO: Report why moves failed
# TODO: Add any todos from both old versions of minesweeper
# TODO: Report bomb count - flag count
# TODO: Flag all bombs on a win
# Also see todos later in the file

import crescent
import hikari
import inspect
import miru
import random
import re
from crescent.ext import docstrings
from dataclasses import dataclass
from enum import Enum
from miru.ext import menu
from PCBot.botdata import BotData
from typing import Awaitable, Callable, Optional

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()
cell_revealed_chars = [
  '\N{LARGE YELLOW SQUARE}',
  '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '\💣'
]

class MinesweeperGridCellState(Enum):
    COVERED   = 1
    FLAGGED   = 2
    REVEALED  = 3


class MinesweeperGameStatus(Enum):
    STARTED = 1
    LOST    = 2
    WON     = 3


class MinesweeperOption(Enum):
    FLAG                      = 1
    REVEAL                    = 2
    FAILED_FLAG_BY_REVEALED   = 3
    FAILED_REVEAL_BY_FLAGGED  = 4
    FAILED_REVEAL_BY_REVEALED = 5


class MinesweeperScreenStage(Enum):
    OPTION = 1
    LETTER = 2
    NUMBER = 3


class MinesweeperInputMethod(Enum):
    SCREEN = 1
    REPLY  = 2


@dataclass
class MinesweeperGridCell:
    revealed_char_idx = 0
    state = MinesweeperGridCellState.COVERED

    def is_bomb(self) -> bool:
        return self.revealed_char_idx == 9

    def make_bomb(self) -> bool:
        was_bomb = self.revealed_char_idx == 9
        self.revealed_char_idx = 9
        return not was_bomb

    def increment_adjacent_bomb_count(self) -> None:
        if self.revealed_char_idx == 9:
            pass
        elif self.revealed_char_idx <= 7:
            self.revealed_char_idx += 1
        else:
            raise Exception('Cannot increment adjacent bomb count past 8')


class MinesweeperGrid:
    """Class to store information about the minesweeper grid."""
    size: int
    bomb_count: int

    grid: list[list[MinesweeperGridCell]]
    generated_mines = False

    def __init__(self, size: int, bomb_count: int):
        self.size = size
        self.bomb_count = bomb_count

        self.grid = [
          [MinesweeperGridCell() for column in range(self.size)]
          for row in range(self.size)
        ]

    def __str__(self) -> str:
        """Convert a grid into a string."""
        # It took ages to find a way to align the grid on discord, the best
        # method found uses a list for the row numbers and regional indicators
        # for the letters. Then to align letters to the grid that line needs to
        # start with the same indent as the list indices which were found by
        # trial and error for single and double digits.
        if self.size <= 9:
            # Braille pattern space, thin space, six-per-em space
            letter_indent = '⠀  '
        elif self.size <= 99:
            # Braille pattern space, figure space, thin space, six-per-em space
            letter_indent = '⠀   '
        else:
            raise Exception(f'First line indent for {self.size} not known')

        a_val = ord('🇦')
        grid_message = (
          f'\n{letter_indent}'
          + ' '.join([chr(a_val + i) for i in range(self.size)])
        )

        global cell_revealed_chars
        for row in range(self.size):
            grid_message += f'\n{row + 1}. '
            for column in range(self.size):
                grid_cell = self.grid[row][column]
                if grid_cell.state is MinesweeperGridCellState.COVERED:
                    grid_message += '\N{LARGE GREEN SQUARE}'
                elif grid_cell.state is MinesweeperGridCellState.FLAGGED:
                    grid_message += '🚩'
                elif grid_cell.state is MinesweeperGridCellState.REVEALED:
                    grid_message += (
                      cell_revealed_chars[grid_cell.revealed_char_idx]
                    )
                else:
                    raise Exception(f'Unexpected cell state {grid_cell.state}')
                grid_message += ' '

        return grid_message

    def get_cell_flagged_status(self, row: int, column: int) -> bool:
        if row >= self.size or column >= self.size:
            raise Exception(f'Cell ({row}, {column}) is out of range')

        grid_cell = self.grid[row][column]
        if grid_cell.state in {
          MinesweeperGridCellState.COVERED,
          MinesweeperGridCellState.REVEALED
        }:
            return False
        elif grid_cell.state is MinesweeperGridCellState.FLAGGED:
            return True
        else:
            raise Exception(f'Unexpected cell state {grid_cell.state}')

    def toggle_cell_flagged_status(self, row: int, column: int) -> None:
        if row >= self.size or column >= self.size:
            raise Exception(f'Cell ({row}, {column}) is out of range')

        grid_cell = self.grid[row][column]
        if grid_cell.state is MinesweeperGridCellState.COVERED:
            grid_cell.state = MinesweeperGridCellState.FLAGGED
        elif grid_cell.state is MinesweeperGridCellState.FLAGGED:
            grid_cell.state = MinesweeperGridCellState.COVERED
        else:
            raise Exception(f'Unexpected cell state {grid_cell.state}')

    def _generate_mines(self, except_row: int, except_column: int) -> None:
        """Randomly scatters bombs in the grid."""
        for bomb in range(self.bomb_count):
            while True:
                row = random.randrange(self.size)
                column = random.randrange(self.size)

                if (abs(row - except_row) <= 1
                    and abs(column - except_column) <= 1):
                        continue

                if self.grid[row][column].make_bomb():
                  break

            north_exists = row > 0
            east_exists = column < self.size - 1
            south_exists = row < self.size - 1
            west_exists = column > 0

            if north_exists:
                self.grid[row - 1][column].increment_adjacent_bomb_count()
            if north_exists and east_exists:
                self.grid[row - 1][column + 1].increment_adjacent_bomb_count()
            if east_exists:
                self.grid[row][column + 1].increment_adjacent_bomb_count()
            if south_exists and east_exists:
                self.grid[row + 1][column + 1].increment_adjacent_bomb_count()
            if south_exists:
                self.grid[row + 1][column].increment_adjacent_bomb_count()
            if south_exists and west_exists:
                self.grid[row + 1][column - 1].increment_adjacent_bomb_count()
            if west_exists:
                self.grid[row][column - 1].increment_adjacent_bomb_count()
            if north_exists and west_exists:
                self.grid[row - 1][column - 1].increment_adjacent_bomb_count()

        self.generated_mines = True

    def get_cell_revealed_status(self, row: int, column: int) -> bool:
        if row >= self.size or column >= self.size:
            raise Exception(f'Cell ({row}, {column}) is out of range')

        grid_cell = self.grid[row][column]
        if grid_cell.state in {
          MinesweeperGridCellState.COVERED,
          MinesweeperGridCellState.FLAGGED
        }:
            return False
        elif grid_cell.state is MinesweeperGridCellState.REVEALED:
            return True
        else:
            raise Exception(f'Unexpected cell state {grid_cell.state}')

    def reveal_cell(self, row: int, column: int, flooding=False) -> None:
        if row >= self.size or column >= self.size:
            raise Exception(f'Cell ({row}, {column}) is out of range')

        grid_cell = self.grid[row][column]
        if grid_cell.state is MinesweeperGridCellState.FLAGGED:
            raise Exception(
              f'Cell ({row}, {column}) is flagged so cannot be uncovered'
            )
        elif grid_cell.state is MinesweeperGridCellState.REVEALED:
            if flooding:
                return
            raise Exception(f'Cell ({row}, {column}) is already revealed')

        if not self.generated_mines:
            self._generate_mines(row, column)

        grid_cell.state = MinesweeperGridCellState.REVEALED

        if grid_cell.revealed_char_idx == 0:
            north_exists = row > 0
            east_exists = column < self.size - 1
            south_exists = row < self.size - 1
            west_exists = column > 0

            if north_exists:
                self.reveal_cell(row - 1, column, True)
            if north_exists and east_exists:
                self.reveal_cell(row - 1, column + 1, True)
            if east_exists:
                self.reveal_cell(row, column + 1, True)
            if south_exists and east_exists:
                self.reveal_cell(row + 1, column + 1, True)
            if south_exists:
                self.reveal_cell(row + 1, column, True)
            if south_exists and west_exists:
                self.reveal_cell(row + 1, column - 1, True)
            if west_exists:
                self.reveal_cell(row, column - 1, True)
            if north_exists and west_exists:
                self.reveal_cell(row - 1, column - 1, True)

    def reveal_bombs(self) -> None:
        for row in range(self.size):
            for column in range(self.size):
                grid_cell = self.grid[row][column]
                if grid_cell.is_bomb():
                    grid_cell.state = MinesweeperGridCellState.REVEALED

    def get_cell_bomb_status(self, row: int, column: int) -> bool:
        if row >= self.size or column >= self.size:
            raise Exception(f'Cell ({row}, {column}) is out of range')

        grid_cell = self.grid[row][column]
        return grid_cell.is_bomb()

    # TODO: track covered_squares to remove the need for the loop
    def check_game_won(self) -> bool:
        covered_squares = 0

        for row in range(self.size):
            for column in range(self.size):
                grid_cell = self.grid[row][column]
                if grid_cell.state is not MinesweeperGridCellState.REVEALED:
                    covered_squares += 1

                if covered_squares > self.bomb_count:
                    return False

        return covered_squares == self.bomb_count


class MinesweeperGame:
    grid: MinesweeperGrid
    status = MinesweeperGameStatus.STARTED

    last_column: Optional[int] = None # Letter
    last_row: Optional[int] = None    # Number
    last_option: Optional[MinesweeperOption] = None
    last_input_method: Optional[MinesweeperInputMethod] = None

    def __init__(self, grid_size: int, bomb_count: int):
        self.grid = MinesweeperGrid(grid_size, bomb_count)

    def __str__(self) -> str:
        status = inspect.cleandoc(
          '''You are playing minesweeper.
          Play using either the buttons below or by replying with a
          message like C7 to reveal a square or fB2 to flag instead.'''
        )

        if (self.last_column is not None and self.last_row is not None
            and self.last_option is not None
            and self.last_input_method is not None):
                status += '\n\nThe last move to was to '

                if self.last_option is MinesweeperOption.FLAG:
                    flagged = self.grid.get_cell_flagged_status(
                      self.last_row, self.last_column
                    )
                    if flagged:
                        status += 'flag'
                    else:
                        status += 'unflag'
                elif (self.last_option is
                       MinesweeperOption.FAILED_FLAG_BY_REVEALED):
                    status += 'try to flag'
                elif self.last_option is MinesweeperOption.REVEAL:
                    status += 'reveal'
                elif self.last_option in {
                  MinesweeperOption.FAILED_REVEAL_BY_FLAGGED,
                  MinesweeperOption.FAILED_REVEAL_BY_REVEALED
                }:
                    status += 'try to reveal'
                else:
                    raise Exception(
                      f'Invalid input option {self.last_option} used.'
                    )

                last_column_letter = chr(ord('A') + self.last_column)
                status += f' cell {last_column_letter}{self.last_row + 1} via '

                if self.last_input_method is MinesweeperInputMethod.SCREEN:
                    status += 'the buttons'
                elif self.last_input_method is MinesweeperInputMethod.REPLY:
                    status += 'reply'
                else:
                    raise Exception(
                      f'Invalid input method {self.last_input_method} used.'
                    )
                status += '.'

        status += f'\n{self.grid}'

        if self.status is MinesweeperGameStatus.LOST:
            status += '\n\nYou have lost the game.'
        elif self.status is MinesweeperGameStatus.WON:
            status += '\n\nYou have won the game!'

        # Discord trims whitespace only lines and new lines preceeding them
        # but not if they contain markup like italics
        return status + '\n_ _'

    def make_move(
      self, row: int, column: int, option: MinesweeperOption,
      input_method: MinesweeperInputMethod
    ) -> None:
        if row >= self.grid.size or column >= self.grid.size:
            return

        self.last_column = column
        self.last_row = row
        self.last_option = option
        self.last_input_method = input_method

        if option is MinesweeperOption.FLAG:
            if self.grid.get_cell_revealed_status(row, column):
                self.last_option = MinesweeperOption.FAILED_FLAG_BY_REVEALED
                return
            self.grid.toggle_cell_flagged_status(row, column)
        elif option is MinesweeperOption.REVEAL:
            if self.grid.get_cell_flagged_status(row, column):
                self.last_option = MinesweeperOption.FAILED_REVEAL_BY_FLAGGED
                return
            if self.grid.get_cell_revealed_status(row, column):
                self.last_option = MinesweeperOption.FAILED_REVEAL_BY_REVEALED
                return

            self.grid.reveal_cell(row, column)

            if self.grid.get_cell_bomb_status(row, column):
                self.status = MinesweeperGameStatus.LOST
                self.grid.reveal_bombs()
            elif self.grid.check_game_won():
                self.status = MinesweeperGameStatus.WON

        else:
            raise Exception(f'Unexpected option {option}')


def create_button(
  label: str,
  callback: Callable[
    [menu.Screen, miru.ViewContext, menu.ScreenButton], Awaitable[None],
  ],
  style = hikari.ButtonStyle.PRIMARY,
  disabled = False,
) -> menu.ScreenButton:
    button = menu.ScreenButton(label, style=style, disabled=disabled)
    button.callback = lambda ctx: callback(ctx, button)
    return button


class MinesweeperScreen(menu.Screen):
    created_initial_buttons = False
    letter: Optional[chr] = None
    state = MinesweeperScreenStage.OPTION

    option: Optional[MinesweeperOption] = None
    game: MinesweeperGame

    def __init__(self, menu: menu.Menu, grid_size: int, bomb_count: int):
        super().__init__(menu)
        self.game = MinesweeperGame(grid_size, bomb_count)

    async def build_content(self) -> menu.ScreenContent:
        if not self.created_initial_buttons:
          self.created_initial_buttons = True
          await self.show_option_buttons()

        return menu.ScreenContent(
          content=str(self.game)
        )

    async def reload(self) -> None:
        game_over = self.game.status in {
          MinesweeperGameStatus.LOST, MinesweeperGameStatus.WON
        }

        if game_over:
            for child in self.menu.children:
                child.disabled = True

        await self.menu.update_message(await self.build_content())

        if game_over:
            games.pop(self.menu.message.id, None)
            self.menu.stop()

    async def show_option_buttons(self) -> None:
        self.menu.clear_items()
        self.menu.add_item(create_button('(Un)flag', self.flag_pressed))
        self.menu.add_item(create_button('Reveal', self.reveal_pressed))
        await self.reload()

    async def show_input_buttons(self) -> None:
        disable = self.game.status is not MinesweeperGameStatus.STARTED
        self.menu.clear_items()

        for i in range(self.game.grid.size):
            if self.state == MinesweeperScreenStage.LETTER:
                label = str(chr(ord('A') + i))
            elif self.state == MinesweeperScreenStage.NUMBER:
                label = str(i + 1)
            else:
                raise Exception(
                  f'Invalid state {self.state} found while updating buttons'
                )
            self.menu.add_item(create_button(f'{label}', self.input_pressed))

        self.menu.add_item(create_button(
          'Back', self.back_pressed, style=hikari.ButtonStyle.DANGER
        ))

        await self.reload()

    async def flag_pressed(
      self, ctx: miru.ViewContext, button: menu.ScreenButton
    ) -> None:
        self.state = MinesweeperScreenStage.LETTER
        self.option = MinesweeperOption.FLAG
        await self.show_input_buttons()

    async def reveal_pressed(
      self, ctx: miru.ViewContext, button: menu.ScreenButton
    ) -> None:
        self.state = MinesweeperScreenStage.LETTER
        self.option = MinesweeperOption.REVEAL
        await self.show_input_buttons()

    async def back_pressed(
      self, ctx: miru.ViewContext, button: menu.ScreenButton
    ) -> None:
        if self.state == MinesweeperScreenStage.LETTER:
            self.state = MinesweeperScreenStage.OPTION
            self.option = None
            await self.show_option_buttons()
        elif self.state == MinesweeperScreenStage.NUMBER:
            self.state = MinesweeperScreenStage.LETTER
            await self.show_input_buttons()
        else:
            raise Exception(
              f'Back button pressed during state {self.state}'
            )

    async def input_pressed(
      self, ctx: miru.ViewContext, button: menu.ScreenButton
    ) -> None:
        if self.state == MinesweeperScreenStage.LETTER:
            self.state = MinesweeperScreenStage.NUMBER
            self.letter = ord(button.label[0]) - ord('A')
            await self.show_input_buttons()
        elif self.state == MinesweeperScreenStage.NUMBER:
            number = int(button.label) - 1
            self.game.make_move(
              number, self.letter, self.option, MinesweeperInputMethod.SCREEN
            )
            self.state = MinesweeperScreenStage.OPTION
            self.option = None
            self.letter = None
            await self.show_option_buttons()
        else:
            raise Exception(
              f'Input button pressed during state {self.state}'
            )

games: dict[hikari.snowflakes.Snowflake, MinesweeperScreen] = {}


@plugin.include
@crescent.event
async def on_message_create(event: hikari.MessageCreateEvent):
    """Handle replies to minesweeper messages containing moves."""
    if event.message.referenced_message is None:
        return
    referenced_message = event.message.referenced_message

    if referenced_message.id not in games:
        return
    game_info = games[referenced_message.id]

    if event.message.content is None:
        return
    message_text = event.message.content

    regex = r'^\s*(f?)\s*([a-x])\s*(\d{1,2})\s*$'
    message_matches = re.search(regex, message_text, re.IGNORECASE)
    if not message_matches:
        return
    message_groups = message_matches.groups()

    if message_groups[0].lower() == 'f':
        option = MinesweeperOption.FLAG
    else:
        option = MinesweeperOption.REVEAL

    column = ord(message_groups[1].upper()[0]) - ord('A')
    if column >= game_info.game.grid.size:
        return

    row = int(message_groups[2]) - 1
    if row >= game_info.game.grid.size:
        return

    game_info.game.make_move(row, column, option, MinesweeperInputMethod.REPLY)
    await game_info.reload()

    await event.message.delete()

@plugin.include
@docstrings.parse_doc
@crescent.command(name='minesweeper')
class MinesweeperCommand:
    """
    Play Minesweeper.

    Requested by Camtas(camtas).
    Implemented by something sensible(somethingsensible) &
                   Camtas(camtas).
    """

    grid_size = crescent.option(
        int, 'Size of minesweeper grid', min_value=3, default=9, max_value=13
    )
    bomb_count = crescent.option(
        int, 'Number of bombs in the grid', min_value=1, default=5, max_value=80
    )

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle minesweeper command being run by showing grid and buttons."""
        minesweeper_menu = menu.Menu()

        screen = MinesweeperScreen(
          minesweeper_menu, self.grid_size, self.bomb_count
        )
        screen_builder = await minesweeper_menu.build_response_async(
            plugin.model.miru, screen
        )

        message = await ctx.respond_with_builder(
          screen_builder, ensure_message=True
        )

        games[message.id] = screen

        plugin.model.miru.start_view(minesweeper_menu, bind_to=message)
