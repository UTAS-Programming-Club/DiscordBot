"""This module contains the bot's checkers minigame command."""
# pyright: strict

from crescent import command, Context, option, Plugin
from colorama import Back, Fore
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

grid_size: int = 8


class CheckersTokenPlayer(Enum):
    PLAYER1 = 1
    PLAYER2 = 2


class CheckersTokenType(Enum):
    EMPTY   = 1
    REGULAR = 2
    KING    = 3


class CheckersGameStatus(Enum):
    STARTED = 1
    LOST    = 2
    WON     = 3


class CheckersInputMethod(Enum):
    BUTTON = 1
    REPLY  = 2


@dataclass
class CheckersGridCell:
    token = CheckersTokenType.EMPTY
    player: Optional[CheckersTokenPlayer] = None


class CheckersGrid:
    """Class to store information about the checkers grid."""
    grid: list[list[CheckersGridCell]]

    def __init__(self):
        self.grid = [
          [CheckersGridCell() for _ in range(grid_size)]
          for _ in range(grid_size)
        ]

        for row in range(3):
            for column in range(grid_size):
                if row % 2 == column % 2:
                    self.grid[grid_size - row - 1][column].token = CheckersTokenType.REGULAR
                    self.grid[grid_size - row - 1][column].player = CheckersTokenPlayer.PLAYER2
                else:
                    self.grid[row][column].token = CheckersTokenType.REGULAR
                    self.grid[row][column].player = CheckersTokenPlayer.PLAYER1

    def __str__(self) -> str:
        """Convert a grid into a string."""
        grid_message: str = '```ansi\n'

        for row in range(grid_size):
            grid_message += '\n'
            for column in range(grid_size):
                grid_cell: CheckersGridCell = self.grid[row][column]

                if row % 2 == column % 2:
                    grid_message += Back.WHITE
                else:
                    grid_message += Back.BLACK

                match grid_cell.player:
                    case CheckersTokenPlayer.PLAYER1:
                        grid_message += Fore.BLUE
                    case CheckersTokenPlayer.PLAYER2:
                        grid_message += Fore.RED

                match grid_cell.token:
                    case CheckersTokenType.EMPTY:
                        grid_message += '    '
                    case CheckersTokenType.REGULAR:
                        # Figure space, six-per-em space, black large circle, figure space, six-per-em space
                        grid_message += '  ⬤  '
                    case CheckersTokenType.KING:
                        #  En quad, thin space, black chess king, en quad, thin space
                        grid_message += '  ♚  '

        return grid_message + '```'


class CheckersGame(TextGuessGame):
    message: Optional[Message] = None
    in_thread: bool = False

    grid: CheckersGrid
    status = CheckersGameStatus.STARTED

    last_input_method: Optional[CheckersInputMethod] = None

    def __init__(self, user_id: Snowflake, multiguesser: bool):
        super().__init__(user_id, multiguesser)

        self.grid = CheckersGrid()

    # TODO: Report already made moves
    def add_guess(self, guess: str) -> GuessOutcome:
        """(Un)Flags or Reveals the guessed cell and reports any issues."""
        if self.message is None:
            return GuessOutcome.Invalid

        # TODO: Implement
        return GuessOutcome.Invalid

    def __str__(self) -> str:
        # line 1
        status = 'You are playing checkers.\n'

        # line 2:
        status += 'Play using either the buttons below or by '
        if self.in_thread:
            status += 'sending'
        else:
            status += 'replying with'
        # status += ' a message like C7 to reveal a square or fB2 to flag instead.\n'

        # if (self.last_column is not None and self.last_row is not None
        #     and self.last_option is not None
        #     and self.last_input_method is not None):
        #         status += '\nThe last move to was to '
        # 
        #         # match self.last_option:
        #         #     case MinesweeperOption.FLAG:
        #         #         flagged = self.grid.get_cell_flagged_status(
        #         #             self.last_row, self.last_column
        #         #         )
        #         #         if not flagged:
        #         #             status += 'un'
        #         #         status += 'flag'
        #         #     case MinesweeperOption.FAILED_FLAG_BY_REVEALED:
        #         #         status += 'try to flag'
        #         #     case MinesweeperOption.REVEAL:
        #         #         status += 'reveal'
        #         #     case (MinesweeperOption.FAILED_REVEAL_BY_FLAGGED
        #         #           | MinesweeperOption.FAILED_REVEAL_BY_REVEALED):
        #         #         status += 'try to reveal'
        # 
        #         # last_column_letter = chr(ord('A') + self.last_column)
        #         # status += f' cell {last_column_letter}{self.last_row + 1} via '
        # 
        #         match self.last_input_method:
        #             case MinesweeperInputMethod.SCREEN:
        #                 status += 'the buttons'
        #             case MinesweeperInputMethod.REPLY:
        #                 status += 'reply'
        #         status += '.\n'
        status += '.\n'

        status += str(self.grid)

        match self.status:
            case CheckersGameStatus.LOST:
                status += '\n\nYou have lost the game.'
            case CheckersGameStatus.WON:
                status += '\n\nYou have won the game!'
            case CheckersGameStatus.STARTED:
                pass

        if (self.message is not None
              and self.status is not CheckersGameStatus.STARTED):
            remove_game(self.message.id)
            remove_game(self.message.channel_id)

        # Discord trims whitespace only lines and new lines preceeding them
        # but not if they contain markup like italics
        return status + '\n_ _'

    # def make_move(
    #   self, row: int, column: int, option: MinesweeperOption,
    #   input_method: CheckersInputMethod
    # ) -> None:
    #     if row >= self.grid.size or column >= self.grid.size:
    #         return
    # 
    #     self.last_column = column
    #     self.last_row = row
    #     self.last_option = option
    #     self.last_input_method = input_method
    # 
    #     match option:
    #         case MinesweeperOption.FLAG:
    #             if self.grid.get_cell_revealed_status(row, column):
    #                 self.last_option = MinesweeperOption.FAILED_FLAG_BY_REVEALED
    #                 return
    #             self.grid.toggle_cell_flagged_status(row, column)
    #         case MinesweeperOption.REVEAL:
    #             if self.grid.get_cell_flagged_status(row, column):
    #                 self.last_option = MinesweeperOption.FAILED_REVEAL_BY_FLAGGED
    #                 return
    #             if self.grid.get_cell_revealed_status(row, column):
    #                 self.last_option = MinesweeperOption.FAILED_REVEAL_BY_REVEALED
    #                 return
    # 
    #             self.grid.reveal_cell(row, column)
    # 
    #             if self.grid.get_cell_bomb_status(row, column):
    #                 self.status = MinesweeperGameStatus.LOST
    #                 self.grid.reveal_bombs()
    #             elif self.grid.check_game_won():
    #                 self.status = MinesweeperGameStatus.WON
    #         case MinesweeperOption.FAILED_FLAG_BY_REVEALED:
    #             # TODO: Report failure
    #             pass
    #         case MinesweeperOption.FAILED_REVEAL_BY_FLAGGED:
    #             # TODO: Report failure
    #             pass
    #         case MinesweeperOption.FAILED_REVEAL_BY_REVEALED:
    #             # TODO: Report failure
    #             pass


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


class CheckersScreen(menu.Screen):
    created_initial_buttons = False
    column: Optional[int] = None

    game: CheckersGame

    def __init__(
      self, menu: menu.Menu, user_id: Snowflake, multiguesser: bool
    ):
        super().__init__(menu)
        self.game = CheckersGame(user_id, multiguesser)

    async def build_content(self) -> menu.ScreenContent:
        if not self.created_initial_buttons:
          self.created_initial_buttons = True
          await self.show_buttons()

        return menu.ScreenContent(content=str(self.game))

    async def reload(self) -> None:
        if self.menu.message is None:
            return

        game_over = self.game.status is not CheckersGameStatus.STARTED

        if game_over:
            for child in self.menu.children:
                child.disabled = True

        await self.menu.update_message(await self.build_content())

        if game_over:
            remove_game(self.menu.message.id)
            remove_game(self.menu.message.channel_id)
            self.menu.stop()

    async def show_buttons(self) -> None:
        disable: bool = self.game.status is not CheckersGameStatus.STARTED
        self.menu.clear_items()

        # for i in range(2):
        self.menu.add_item(
          create_button('test', self.button_pressed, disabled=disable)  # pyright: ignore [reportArgumentType]
        )

        await self.reload()

    async def button_pressed(
      self, ctx: ViewContext, button: menu.ScreenButton
    ) -> None:
        pass

game_screens: dict[CheckersGame, CheckersScreen] = {}

@plugin.include
@docstrings.parse_doc
@command(name='checkers')
class CheckersCommand:
    """
    Play a game of Checkers.

    Requested by Lachlan McKay(emiko_namami) & Taylor(randomsploosh).
    Implemented by Joshua(somethingsensible) & Lachlan McKay(emiko_namami).
    """

    multiguesser = option(bool, 'Allow anyone to guess', default=False)
    thread = option(bool, 'Automatically create a thread', default=False)

    async def callback(self, ctx: Context) -> None:
        """Handle checkers command being run by showing grid and buttons."""
        checkers_menu = menu.Menu()
        screen = CheckersScreen(checkers_menu, ctx.user.id, self.multiguesser)

        in_correct_thread: bool
        channel: Optional[TextableGuildChannel]
        in_correct_thread, channel = await get_interaction_channel(
          ctx, 'Checkers'
        )
        in_thread: bool = (
          channel is not None and channel.type is ChannelType.GUILD_PUBLIC_THREAD
        )

        screen.game.in_thread = (not in_thread and self.thread) or in_correct_thread
        screen_builder = await checkers_menu.build_response_async(
            plugin.model.miru, screen
        )
        game_screens[screen.game] = screen

        # TODO: Report want_thread being ignored if in wrong thread?
        if not in_thread and self.thread:
            # TODO: Avoid this message
            await ctx.respond(
              'Starting checkers game in thread!', ephemeral=True
            )

            thread: GuildThreadChannel = await ctx.app.rest.create_thread(
              ctx.channel_id, ChannelType.GUILD_PUBLIC_THREAD, 'Checkers'
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
          checkers_menu, bind_to=screen.game.message
        )
