"""This module contains the bot's minesweeper minigame command."""
# pyright: strict

# TODO: Figure out why some chars stop appearing for 14x14 despite being well
# below the length limit. I tried copying the message and reposting it and hit
# the same issue so it is not bot specific.
# TODO: Add messages that check for and prevent exceptions from occurring
# TODO: Ensure bomb count is capped at grid size * grid_size - 1
# TODO: Switch from bomb to boom char?
# TODO: Add custom emoji to the bot that is the flag one on top of the green square one
# TODO: Report expiry
# TODO: Report why moves failed
# TODO: Add any todos from both old versions of minesweeper
# TODO: Report bomb count - flag count
# TODO: Flag all bombs on a win
# Also see todos later in the file

from crescent import command, Context, option, Plugin
from crescent.ext import docstrings
from dataclasses import dataclass
from enum import Enum
from hikari import (
  ButtonStyle, ChannelType, GatewayBot, Message, GuildThreadChannel, Snowflake,
  TextableGuildChannel
)
from miru import ViewContext
from miru.ext import menu
from miru.internal.types import InteractiveButtonStylesT
from random import randrange
from re import Match, IGNORECASE, search
from typing import Awaitable, Callable, Optional
from PCBot.botdata import BotData
from PCBot.plugins.replyhandler import (
  add_game, get_interaction_channel, GuessOutcome, remove_game, TextGuessGame
)

plugin = Plugin[GatewayBot, BotData]()
cell_revealed_chars = [
  '\N{LARGE YELLOW SQUARE}',
  '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '\\💣'
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
    revealed_char_idx: int = 0
    state = MinesweeperGridCellState.COVERED

    def is_bomb(self) -> bool:
        return self.revealed_char_idx == 9

    def make_bomb(self) -> bool:
        was_bomb: bool = self.revealed_char_idx == 9
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
    generated_mines: bool = False

    def __init__(self, size: int, bomb_count: int):
        self.size = size
        self.bomb_count = bomb_count

        self.grid = [
          [MinesweeperGridCell() for _ in range(self.size)]
          for _ in range(self.size)
        ]

    def __str__(self) -> str:
        """Convert a grid into a string."""
        # It took ages to find a way to align the grid on discord, the best
        # method found uses a list for the row numbers and regional indicators
        # for the letters. Then to align letters to the grid that line needs to
        # start with the same indent as the list indices which were found by
        # trial and error for single and double digits.
        letter_indent: str
        if self.size <= 9:
            # Braille pattern space, thin space, six-per-em space
            letter_indent = '⠀  '
        elif self.size <= 99:
            # Braille pattern space, figure space, thin space, six-per-em space
            letter_indent = '⠀   '
        else:
            raise Exception(f'First line indent for {self.size} not known')

        a_val: int = ord('🇦')
        grid_message: str = (
          f'\n{letter_indent}'
          + ' '.join([chr(a_val + i) for i in range(self.size)])
        )

        global cell_revealed_chars
        for row in range(self.size):
            grid_message += f'\n{row + 1}. '
            for column in range(self.size):
                grid_cell: MinesweeperGridCell = self.grid[row][column]
                match grid_cell.state:
                    case MinesweeperGridCellState.COVERED:
                        grid_message += '\N{LARGE GREEN SQUARE}'
                    case MinesweeperGridCellState.FLAGGED:
                        grid_message += '🚩'
                    case MinesweeperGridCellState.REVEALED:
                        grid_message += (
                          cell_revealed_chars[grid_cell.revealed_char_idx]
                        )
                grid_message += ' '

        return grid_message

    def get_cell_flagged_status(self, row: int, column: int) -> bool:
        if row >= self.size or column >= self.size:
            raise Exception(f'Cell ({row}, {column}) is out of range')

        grid_cell: MinesweeperGridCell = self.grid[row][column]
        return grid_cell.state is MinesweeperGridCellState.FLAGGED

    def toggle_cell_flagged_status(self, row: int, column: int) -> None:
        if row >= self.size or column >= self.size:
            raise Exception(f'Cell ({row}, {column}) is out of range')

        grid_cell: MinesweeperGridCell = self.grid[row][column]
        match grid_cell.state:
            case MinesweeperGridCellState.COVERED:
                grid_cell.state = MinesweeperGridCellState.FLAGGED
            case MinesweeperGridCellState.FLAGGED:
                grid_cell.state = MinesweeperGridCellState.COVERED
            case MinesweeperGridCellState.REVEALED:
                    # TODO: Report failure
                    pass

    def _generate_mines(self, except_row: int, except_column: int) -> None:
        """Randomly scatters bombs in the grid."""
        for _ in range(self.bomb_count):
            while True:
                row: int = randrange(self.size)
                column: int = randrange(self.size)

                if (abs(row - except_row) <= 1
                    and abs(column - except_column) <= 1):
                        continue

                if self.grid[row][column].make_bomb():
                  break

            north_exists: bool = row > 0
            east_exists: bool = column < self.size - 1
            south_exists: bool = row < self.size - 1
            west_exists: bool = column > 0

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

        grid_cell: MinesweeperGridCell = self.grid[row][column]
        return grid_cell.state is MinesweeperGridCellState.REVEALED

    def reveal_cell(self, row: int, column: int, flooding: bool=False) -> None:
        if row >= self.size or column >= self.size:
            raise Exception(f'Cell ({row}, {column}) is out of range')

        grid_cell: MinesweeperGridCell = self.grid[row][column]
        match grid_cell.state:
            case MinesweeperGridCellState.FLAGGED:
                raise Exception(
                    f'Cell ({row}, {column}) is flagged so cannot be uncovered'
                )
            case MinesweeperGridCellState.REVEALED:
                if flooding:
                    return
                raise Exception(f'Cell ({row}, {column}) is already revealed')
            case MinesweeperGridCellState.COVERED:
                # TODO: Report failure
                pass

        if not self.generated_mines:
            self._generate_mines(row, column)

        grid_cell.state = MinesweeperGridCellState.REVEALED

        if grid_cell.revealed_char_idx == 0:
            north_exists: bool = row > 0
            east_exists: bool = column < self.size - 1
            south_exists: bool = row < self.size - 1
            west_exists: bool = column > 0

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

        grid_cell: MinesweeperGridCell = self.grid[row][column]
        return grid_cell.is_bomb()

    # TODO: track covered_squares to remove the need for the loop
    def check_game_won(self) -> bool:
        covered_squares: int = 0

        for row in range(self.size):
            for column in range(self.size):
                grid_cell: MinesweeperGridCell = self.grid[row][column]
                if grid_cell.state is not MinesweeperGridCellState.REVEALED:
                    covered_squares += 1

                if covered_squares > self.bomb_count:
                    return False

        return covered_squares == self.bomb_count


class MinesweeperGame(TextGuessGame):
    message: Optional[Message] = None
    in_thread: bool = False

    grid: MinesweeperGrid
    status = MinesweeperGameStatus.STARTED

    last_column: Optional[int] = None # Letter
    last_row: Optional[int] = None    # Number
    last_option: Optional[MinesweeperOption] = None
    last_input_method: Optional[MinesweeperInputMethod] = None

    def __init__(
      self, user_id: Snowflake, multiguesser: bool, grid_size: int,
      bomb_count: int
    ):
        super().__init__(user_id, multiguesser)

        self.grid = MinesweeperGrid(grid_size, bomb_count)

    # TODO: Report already made moves
    def add_guess(self, guess: str) -> GuessOutcome:
        """(Un)Flags or Reveals the guessed cell and reports any issues."""
        if self.message is None:
            return GuessOutcome.Invalid

        regex: str = r'^\s*(f?)\s*([a-x])\s*(\d{1,2})\s*$'
        guess_matches: Optional[Match[str]] = search(regex, guess, IGNORECASE)
        if not guess_matches:
            return GuessOutcome.Invalid
        guess_groups: tuple[str, ...] = guess_matches.groups()

        option: MinesweeperOption
        if guess_groups[0].lower() == 'f':
            option = MinesweeperOption.FLAG
        else:
            option = MinesweeperOption.REVEAL

        column: int = ord(guess_groups[1].upper()[0]) - ord('A')
        if column >= self.grid.size:
            return GuessOutcome.Invalid

        row = int(guess_groups[2]) - 1
        if row >= self.grid.size:
            return GuessOutcome.Invalid

        self.make_move(
          row, column, option, MinesweeperInputMethod.REPLY
        )

        return GuessOutcome.Valid

    def __str__(self) -> str:
        if self.message is None:
            return ''

        # line 1
        status = 'You are playing minesweeper.\n'

        # line 2:
        status += 'Play using either the buttons below or by '
        if self.in_thread:
            status += 'sending'
        else:
            status += 'replying with'
        status += ' a message like C7 to reveal a square or fB2 to flag instead.\n'

        if (self.last_column is not None and self.last_row is not None
            and self.last_option is not None
            and self.last_input_method is not None):
                status += '\nThe last move to was to '

                match self.last_option:
                    case MinesweeperOption.FLAG:
                        flagged = self.grid.get_cell_flagged_status(
                            self.last_row, self.last_column
                        )
                        if not flagged:
                            status += 'un'
                        status += 'flag'
                    case MinesweeperOption.FAILED_FLAG_BY_REVEALED:
                        status += 'try to flag'
                    case MinesweeperOption.REVEAL:
                        status += 'reveal'
                    case (MinesweeperOption.FAILED_REVEAL_BY_FLAGGED
                          | MinesweeperOption.FAILED_REVEAL_BY_REVEALED):
                        status += 'try to reveal'

                last_column_letter = chr(ord('A') + self.last_column)
                status += f' cell {last_column_letter}{self.last_row + 1} via '

                match self.last_input_method:
                    case MinesweeperInputMethod.SCREEN:
                        status += 'the buttons'
                    case MinesweeperInputMethod.REPLY:
                        status += 'reply'
                status += '.\n'

        status += str(self.grid)

        match self.status:
            case MinesweeperGameStatus.LOST:
                status += '\n\nYou have lost the game.'
            case MinesweeperGameStatus.WON:
                status += '\n\nYou have won the game!'
            case MinesweeperGameStatus.STARTED:
                pass

        if self.status is not MinesweeperGameStatus.STARTED:
            remove_game(self.message.id)
            remove_game(self.message.channel_id)

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

        match option:
            case MinesweeperOption.FLAG:
                if self.grid.get_cell_revealed_status(row, column):
                    self.last_option = MinesweeperOption.FAILED_FLAG_BY_REVEALED
                    return
                self.grid.toggle_cell_flagged_status(row, column)
            case MinesweeperOption.REVEAL:
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
            case MinesweeperOption.FAILED_FLAG_BY_REVEALED:
                # TODO: Report failure
                pass
            case MinesweeperOption.FAILED_REVEAL_BY_FLAGGED:
                # TODO: Report failure
                pass
            case MinesweeperOption.FAILED_REVEAL_BY_REVEALED:
                # TODO: Report failure
                pass


def create_button(
  label: str,
  callback: Callable[
    [menu.Screen, ViewContext, menu.ScreenButton], Awaitable[None],
  ],
  style: InteractiveButtonStylesT = ButtonStyle.PRIMARY,
  disabled: bool = False,
) -> menu.ScreenButton:
    button = menu.ScreenButton(label, style=style, disabled=disabled)
    # TODO: Fix reportUnknownLambdaType
    button.callback = lambda ctx: callback(ctx, button)  # pyright: ignore [reportCallIssue, reportUnknownLambdaType]
    return button


class MinesweeperScreen(menu.Screen):
    created_initial_buttons = False
    column: Optional[int] = None
    state = MinesweeperScreenStage.OPTION

    option: Optional[MinesweeperOption] = None
    game: MinesweeperGame

    def __init__(
      self, menu: menu.Menu, user_id: Snowflake, multiguesser: bool,
      grid_size: int, bomb_count: int
    ):
        super().__init__(menu)
        self.game = MinesweeperGame(
          user_id, multiguesser, grid_size, bomb_count
        )

    async def build_content(self) -> menu.ScreenContent:
        if not self.created_initial_buttons:
          self.created_initial_buttons = True
          await self.show_option_buttons()

        return menu.ScreenContent(content=str(self.game))

    async def reload(self) -> None:
        if self.menu.message is None:
            return

        game_over = self.game.status is not MinesweeperGameStatus.STARTED

        if game_over:
            for child in self.menu.children:
                child.disabled = True

        await self.menu.update_message(await self.build_content())

        if game_over:
            remove_game(self.menu.message.id)
            remove_game(self.menu.message.channel_id)
            self.menu.stop()

    async def show_option_buttons(self) -> None:
        self.menu.clear_items()
        self.menu.add_item(create_button('(Un)flag', self.flag_pressed))  # pyright: ignore [reportArgumentType]
        self.menu.add_item(create_button('Reveal', self.reveal_pressed))  # pyright: ignore [reportArgumentType]
        await self.reload()

    async def show_input_buttons(self) -> None:
        disable: bool = self.game.status is not MinesweeperGameStatus.STARTED
        self.menu.clear_items()

        for i in range(self.game.grid.size):
            label: str
            match self.state:
                case MinesweeperScreenStage.LETTER:
                    label = chr(ord('A') + i)
                case MinesweeperScreenStage.NUMBER:
                    label = str(i + 1)
                case MinesweeperScreenStage.OPTION:
                    raise Exception(
                      f'Invalid state {self.state} found while updating' +
                      'buttons'
                    )
            self.menu.add_item(
              create_button(f'{label}', self.input_pressed, disabled=disable)  # pyright: ignore [reportArgumentType]
            )

        self.menu.add_item(create_button(
          'Back', self.back_pressed, style=ButtonStyle.DANGER, disabled=disable  # pyright: ignore [reportArgumentType]
        ))

        await self.reload()

    async def flag_pressed(
      self, ctx: ViewContext, button: menu.ScreenButton
    ) -> None:
        self.state = MinesweeperScreenStage.LETTER
        self.option = MinesweeperOption.FLAG
        await self.show_input_buttons()

    async def reveal_pressed(
      self, ctx: ViewContext, button: menu.ScreenButton
    ) -> None:
        self.state = MinesweeperScreenStage.LETTER
        self.option = MinesweeperOption.REVEAL
        await self.show_input_buttons()

    async def back_pressed(
      self, ctx: ViewContext, button: menu.ScreenButton
    ) -> None:
        match self.state:
            case MinesweeperScreenStage.LETTER:
                self.state = MinesweeperScreenStage.OPTION
                self.option = None
                await self.show_option_buttons()
            case MinesweeperScreenStage.NUMBER:
                self.state = MinesweeperScreenStage.LETTER
                await self.show_input_buttons()
            case MinesweeperScreenStage.OPTION:
                raise Exception(
                  f'Back button pressed during state {self.state}'
                )

    async def input_pressed(
      self, ctx: ViewContext, button: menu.ScreenButton
    ) -> None:
        if button.label is None:
            return

        match self.state:
            case MinesweeperScreenStage.LETTER:
                self.state = MinesweeperScreenStage.NUMBER
                self.column = ord(button.label[0]) - ord('A')
                await self.show_input_buttons()
            case MinesweeperScreenStage.NUMBER:
                if self.option is None or self.column is None:
                    return

                row: int = int(button.label) - 1
                self.game.make_move(
                    row, self.column, self.option,
                    MinesweeperInputMethod.SCREEN
                )
                self.state = MinesweeperScreenStage.OPTION
                self.option = None
                self.column = None
                await self.show_option_buttons()
            case MinesweeperScreenStage.OPTION:
                raise Exception(
                  f'Input button pressed during state {self.state}'
                )

game_screens: dict[MinesweeperGame, MinesweeperScreen] = {}

@plugin.include
@docstrings.parse_doc
@command(name='minesweeper')
class MinesweeperCommand:
    """
    Play a game of Minesweeper.

    Requested by Cam(camtas).
    Implemented by Cam(camtas) & Joshua(somethingsensible).
    """

    grid_size = option(
        int, 'Size of minesweeper grid', min_value=3, default=9, max_value=13
    )
    bomb_count = option(
        int, 'Number of bombs in the grid', min_value=1, default=5,
        max_value=80
    )

    multiguesser = option(bool, 'Allow anyone to guess', default=False)
    thread = option(bool, 'Automatically create a thread', default=False)

    async def callback(self, ctx: Context) -> None:
        """Handle minesweeper command being run by showing grid and buttons."""
        minesweeper_menu = menu.Menu()
        screen = MinesweeperScreen(
          minesweeper_menu, ctx.user.id, self.multiguesser, self.grid_size,
          self.bomb_count
        )

        in_correct_thread: bool
        channel: Optional[TextableGuildChannel]
        in_correct_thread, channel = await get_interaction_channel(
          ctx, 'Minesweeper'
        )
        in_thread: bool = (
          channel is not None and channel.type is ChannelType.GUILD_PUBLIC_THREAD
        )

        screen.game.in_thread = (not in_thread and self.thread) or in_correct_thread
        screen_builder = await minesweeper_menu.build_response_async(
            plugin.model.miru, screen
        )
        game_screens[screen.game] = screen

        # TODO: Report want_thread being ignored if in wrong thread?
        if not in_thread and self.thread:
            # TODO: Avoid this message
            await ctx.respond(
              'Starting minesweeper game in thread!', ephemeral=True
            )

            thread: GuildThreadChannel = await ctx.app.rest.create_thread(
              ctx.channel_id, ChannelType.GUILD_PUBLIC_THREAD, 'Minesweeper'
            )
            screen.game.message = await screen_builder.send_to_channel(thread)

            add_game(thread.id, screen.game)
        else:
            if channel is not None and in_correct_thread:
                add_game(channel.id, screen.game)

            screen.game.message = await ctx.respond_with_builder(
              screen_builder, ensure_message=True
            )
            assert screen.game.message is not None

        add_game(screen.game.message.id, screen.game)

        plugin.model.miru.start_view(
          minesweeper_menu, bind_to=screen.game.message
        )
