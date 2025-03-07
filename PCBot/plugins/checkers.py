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
from logging import getLogger, Logger
from miru import ViewContext
from miru.ext.menu import Menu, Screen, ScreenButton, ScreenContent
from miru.internal.types import InteractiveButtonStylesT
from random import randrange
from re import Match, IGNORECASE, search
from typing import Awaitable, Callable, Optional
from PCBot.botdata import BotData
from PCBot.plugins.replyhandler import (
  add_game, get_interaction_channel, GuessOutcome, remove_game, TextGuessGame
)

logger: Logger = getLogger(__name__)
plugin = Plugin[GatewayBot, BotData]()

board_size: int = 8


class CheckersPlayer(Enum):
    PLAYER1 = 1 # Moves up
    PLAYER2 = 2 # Moves down


class CheckersTokenType(Enum):
    EMPTY   = 1
    REGULAR = 2
    KING    = 3


class CheckersGameStatus(Enum):
    STARTED = 1
    LOST    = 2
    WON     = 3


class CheckersScreenStage(Enum):
    TOKEN  = 1
    TARGET = 2


class CheckersInputMethod(Enum):
    BUTTON = 1
    REPLY  = 2


@dataclass(frozen=True)
class CheckersBoardPosition:
    row: int
    column: int


@dataclass
class CheckersBoardCell:
    token = CheckersTokenType.EMPTY
    player: Optional[CheckersPlayer] = None

    def can_move_up(self) -> bool:
        return (
          self.player is CheckersPlayer.PLAYER1 or
          self.token  is CheckersTokenType.KING
        )

    def can_move_down(self) -> bool:
        return (
          self.player is CheckersPlayer.PLAYER2 or
          self.token  is CheckersTokenType.KING
        )


class CheckersBoard:
    """Class to store information about the checkers board."""
    _board: list[list[CheckersBoardCell]]
    _valid_moves: Optional[
      dict[CheckersBoardPosition, set[CheckersBoardPosition]]
    ] = None

    def __init__(self):
        self._board = [
          [CheckersBoardCell() for _ in range(board_size)]
          for _ in range(board_size)
        ]

        for row in range(3):
            for column in range(board_size):
                if row % 2 == column % 2:
                    self._board[board_size - row - 1][column].token = CheckersTokenType.REGULAR
                    self._board[board_size - row - 1][column].player = CheckersPlayer.PLAYER1
                else:
                    self._board[row][column].token = CheckersTokenType.REGULAR
                    self._board[row][column].player = CheckersPlayer.PLAYER2

    def get_board(
      self, stage: CheckersScreenStage, token: Optional[CheckersBoardPosition]
    ) -> str:
        """Convert a board into a string."""
        board_message: str = '```ansi\n'

        for row in range(board_size):
            board_message += '\n'
            for column in range(board_size):
                board_cell: CheckersBoardCell = self._board[row][column]
                position = CheckersBoardPosition(row, column)

                highlight_token: bool = (
                  stage is CheckersScreenStage.TOKEN and
                  self._valid_moves is not None and
                  position in self._valid_moves and
                  len(self._valid_moves[position]) > 0
                )

                highlight_cell: bool = (
                  stage is CheckersScreenStage.TARGET and
                  self._valid_moves is not None and
                  token in self._valid_moves and
                  position in self._valid_moves[token]
                )

                match board_cell.player:
                    case CheckersPlayer.PLAYER1:
                        if highlight_token:
                            board_message += Fore.CYAN
                        else:
                            board_message += Fore.BLUE
                    case CheckersPlayer.PLAYER2:
                        if highlight_token:
                            board_message += Fore.MAGENTA
                        else:
                            board_message += Fore.RED

                if row % 2 == column % 2:
                    board_message += Back.WHITE
                elif highlight_cell:
                    board_message += Back.BLUE # Gray on Discord
                else:
                    board_message += Back.BLACK # Firefly dark blue on Discord

                match board_cell.token:
                    case CheckersTokenType.EMPTY:
                        board_message += '    '
                    case CheckersTokenType.REGULAR:
                        # Figure space, six-per-em space, black large circle, figure space, six-per-em space
                        board_message += '  ⬤  '
                    case CheckersTokenType.KING:
                        #  En quad, thin space, black chess king, en quad, thin space
                        board_message += '  ♚  '

        return board_message + '```'

    def get_valid_moves(
      self, player: CheckersPlayer, force: bool = False
    ) -> dict[CheckersBoardPosition, set[CheckersBoardPosition]]:
        if self._valid_moves is not None and not force:
            return self._valid_moves

        self._valid_moves = {}

        for row in range(board_size):
            for column in range(board_size):
                board_cell: CheckersBoardCell = self._board[row][column]
                valid_moves: set[CheckersBoardPosition] = set()

                if board_cell.player is not player:
                    continue

                can_move_up:   bool = board_cell.can_move_up()
                can_move_down: bool = board_cell.can_move_down()

                # Up and left
                if can_move_up and row > 0 and column > 0:
                    next_cell: CheckersBoardCell = (
                        self._board[row - 1][column - 1]
                    )
                    if next_cell.token is CheckersTokenType.EMPTY:
                        valid_moves.add(CheckersBoardPosition(row - 1, column - 1))
                    elif next_cell.player is not player and row > 1 and column > 1:
                        next_cell = self._board[row - 2][column - 2]
                        if next_cell.token is CheckersTokenType.EMPTY:
                            valid_moves.add(CheckersBoardPosition(row - 2, column - 2))

                # Up and right
                if can_move_up and row > 0 and column < board_size - 1:
                    next_cell: CheckersBoardCell = (
                        self._board[row - 1][column + 1]
                    )
                    if next_cell.token is CheckersTokenType.EMPTY:
                        valid_moves.add(CheckersBoardPosition(row - 1, column + 1))
                    elif next_cell.player is not player and row > 1 and column < board_size - 2:
                        next_cell = self._board[row - 2][column + 2]
                        if next_cell.token is CheckersTokenType.EMPTY:
                            valid_moves.add(CheckersBoardPosition(row - 2, column + 2))

                # Down and left
                if can_move_down and row < board_size - 1 and column > 0:
                    next_cell: CheckersBoardCell = (
                        self._board[row + 1][column - 1]
                    )
                    if next_cell.token is CheckersTokenType.EMPTY:
                        valid_moves.add(CheckersBoardPosition(row + 1, column - 1))
                    elif next_cell.player is not player and row < board_size - 2 and column > 1:
                        next_cell = self._board[row + 2][column - 2]
                        if next_cell.token is CheckersTokenType.EMPTY:
                            valid_moves.add(CheckersBoardPosition(row + 2, column - 2))

                # Down and right
                if can_move_down and row < board_size - 1 and column < board_size - 1:
                    next_cell: CheckersBoardCell = (
                        self._board[row + 1][column + 1]
                    )
                    if next_cell.token is CheckersTokenType.EMPTY:
                        valid_moves.add(CheckersBoardPosition(row + 1, column + 1))
                    elif next_cell.player is not player and row < board_size - 2 and column < board_size - 2:
                        next_cell = self._board[row + 2][column + 2]
                        if next_cell.token is CheckersTokenType.EMPTY:
                            valid_moves.add(CheckersBoardPosition(row + 2, column + 2))

                if len(valid_moves) > 0:
                    self._valid_moves[CheckersBoardPosition(row, column)] = valid_moves

        return self._valid_moves


class CheckersGame(TextGuessGame):
    message: Optional[Message] = None
    in_thread: bool = False

    board: CheckersBoard
    status = CheckersGameStatus.STARTED
    player = CheckersPlayer.PLAYER1

    # These should be in CheckersScreen but they are needed for CheckersBoard.get_board
    # which is called from __str__ which cannot take parameters
    stage = CheckersScreenStage.TOKEN
    token: Optional[CheckersBoardPosition] = None

    # last_token: Optional[CheckersBoardPosition] = None
    # last_target: Optional[CheckersBoardPosition] = None
    # last_removed: Optional[CheckersBoardPosition] = None
    last_input_method: Optional[CheckersInputMethod] = None

    def __init__(self, user_id: Snowflake, multiguesser: bool):
        super().__init__(user_id, multiguesser)

        self.board = CheckersBoard()

    # TODO: Report already made moves
    def add_guess(self, guess: str) -> GuessOutcome:
        """(Un)Flags or Reveals the guessed cell and reports any issues."""
        if self.message is None:
            return GuessOutcome.Invalid

        # TODO: Implement

        # Cache updated list of valid moves
        self.game.board.get_valid_moves(self.player, True)
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
        status += ' a message like (1, 5), (2, 6) to move a token to a new position.\n'

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

        status += self.board.get_board(self.stage, self.token)

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

    def make_move(
      self, # row: int, column: int, option: MinesweeperOption,
      # input_method: CheckersInputMethod
    ) -> None:
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
        pass


def create_button(
  label: str,
  callback: Callable[[Screen, ViewContext, ScreenButton], Awaitable[None]],
  style: InteractiveButtonStylesT = ButtonStyle.PRIMARY,
  disabled: bool = False,
) -> ScreenButton:
    button = ScreenButton(label, style=style, disabled=disabled)
    # TODO: Fix reportUnknownLambdaType
    button.callback = lambda ctx: callback(ctx, button)  # pyright: ignore [reportCallIssue, reportUnknownLambdaType]
    return button


class CheckersScreen(Screen):
    created_initial_buttons = False

    game: CheckersGame

    def __init__(self, menu: Menu, user_id: Snowflake, multiguesser: bool):
        super().__init__(menu)
        self.game = CheckersGame(user_id, multiguesser)

    async def build_content(self) -> ScreenContent:
        if not self.created_initial_buttons:
          self.created_initial_buttons = True
          await self.show_buttons()

        return ScreenContent(content=str(self.game))

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
        self.menu.clear_items()
        match self.game.stage:
          case CheckersScreenStage.TOKEN:
              await self.show_token_buttons()
          case CheckersScreenStage.TARGET:
              await self.show_target_buttons()
        await self.reload()

    async def show_token_buttons(self) -> None:
        valid_moves: dict[CheckersBoardPosition, set[CheckersBoardPosition]] = (
            self.game.board.get_valid_moves(self.game.player)
        )

        token: CheckersBoardPosition
        for token in valid_moves:
            label = f'({token.row + 1}, {token.column + 1})'

            self.menu.add_item(create_button(label, self.token_pressed))  # pyright: ignore [reportArgumentType]

    async def show_target_buttons(self) -> None:
        valid_moves: dict[CheckersBoardPosition, set[CheckersBoardPosition]] = (
            self.game.board.get_valid_moves(self.game.player)
        )

        target: CheckersBoardPosition
        for target in valid_moves[self.game.token]:
            label = f'({target.row + 1}, {target.column + 1})'

            self.menu.add_item(create_button(label, self.target_pressed))  # pyright: ignore [reportArgumentType]

    async def token_pressed(
      self, ctx: ViewContext, button: ScreenButton
    ) -> None:
        if button.label is None:
            return

        row = int(button.label[1]) - 1
        column = int(button.label[4]) - 1
        self.game.token = CheckersBoardPosition(row, column)
        self.game.stage = CheckersScreenStage.TARGET
        
        await self.show_buttons()

    async def target_pressed(
      self, ctx: ViewContext, button: ScreenButton
    ) -> None:
        self.game.stage = CheckersScreenStage.TOKEN
        await self.show_buttons()

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
        """Handle checkers command being run by showing board and buttons."""
        logger.info(
          f'{ctx.user} is starting a game(multiguesser: {self.multiguesser},' +
          f' thread: {self.thread})'
        )

        checkers_menu = Menu()
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
