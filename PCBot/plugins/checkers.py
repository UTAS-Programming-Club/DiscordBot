"""This module contains the bot's checkers minigame command."""
# pyright: strict

# TODO: cell size still being the same.
# It's wrong and different on web, desktop, modern mobile, and native mobile.

from colorama import Back, Fore, Style
from crescent import command, Context, option, Plugin
from crescent.ext import docstrings
from crescent.utils import create_task
from dataclasses import dataclass
from enum import Enum
from hikari import (
  ButtonStyle, ChannelType, GatewayBot, Message, GuildThreadChannel, Snowflake,
  TextableGuildChannel, User
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
    STARTED     = 1
    PLAYER1_WON = 2
    PLAYER2_WON = 3


class CheckersScreenStage(Enum):
    TOKEN  = 1
    TARGET = 2


class CheckersInputMethod(Enum):
    SCREEN = 1
    REPLY  = 2


@dataclass(frozen=True)
class CheckersBoardPosition:
    row: int
    column: int

    def __str__(self) -> str:
        row_number = str(board_size - self.row)
        column_letter: str = chr(ord('A') + self.column)
        return f'{column_letter}{row_number}'


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
    # TODO: Switch to dict[CheckersBoardPosition, CheckersBoardCell]?
    board: list[list[CheckersBoardCell]]
    _valid_moves: Optional[
      dict[CheckersBoardPosition, set[tuple[bool, CheckersBoardPosition]]]
    ] = None

    def __init__(self):
        self.board = [
          [CheckersBoardCell() for _ in range(board_size)]
          for _ in range(board_size)
        ]

        for row in range(3):
            for column in range(board_size):
                if row % 2 == column % 2:
                    self.board[board_size - row - 1][column].token = CheckersTokenType.REGULAR
                    self.board[board_size - row - 1][column].player = CheckersPlayer.PLAYER1
                else:
                    self.board[row][column].token = CheckersTokenType.REGULAR
                    self.board[row][column].player = CheckersPlayer.PLAYER2

    def get_board(
      self, stage: CheckersScreenStage, token: Optional[CheckersBoardPosition],
      legacy: bool
    ) -> str:
        """Convert a board into a string."""
        board_message: str = '```ansi\n'

        target_positions: Optional[set[CheckersBoardPosition]] = None
        if (stage is CheckersScreenStage.TARGET and
          self._valid_moves is not None and
          token in self._valid_moves):
            target_positions = {move[1] for move in self._valid_moves[token]}

        # Three-per-em space
        cell_padding = ' '
        # Thin space
        # Used for regular chars(letters and space)
        full_padding: str = cell_padding + ' '

        underline: str
        reset_underline: str
        reset_all: str
        if legacy:
            underline = ''
            reset_underline = ''
            reset_all = ''
        else:
            # ESC[1;2m and ESC[22m, neither are in colorama as it doesn't do style
            underline = '[1;2m'
            reset_underline = '[22m'
            reset_all = Style.RESET_ALL


        board_message += reset_all + underline + '  '
        for column in range(board_size):
            column_letter: str = chr(ord('A') + column)
            board_message += full_padding + column_letter + full_padding

        for row in range(board_size):
            row_number = str(board_size - row)
            board_message += '\n' + reset_all
            board_message += underline + row_number + reset_underline
            board_message += ' '

            for column in range(board_size):
                cell: CheckersBoardCell = self.board[row][column]
                position = CheckersBoardPosition(row, column)

                highlight_token: bool = (
                  stage is CheckersScreenStage.TOKEN and
                  self._valid_moves is not None and
                  position in self._valid_moves and
                  # TODO: Check if this is needed
                  len(self._valid_moves[position]) > 0
                )

                highlight_cell: bool = (
                  target_positions is not None and
                  position in target_positions
                )

                if not legacy:
                    match cell.player:
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

                if cell.token is CheckersTokenType.EMPTY:
                    board_message += full_padding + ' ' + full_padding
                else:
                    board_message += cell_padding
                    if (cell.token is CheckersTokenType.REGULAR and
                          cell.player is CheckersPlayer.PLAYER1):
                        # Bold Circled White Bullet
                        board_message += underline + '⦾' + reset_underline
                    elif (cell.token is CheckersTokenType.KING and
                          cell.player is CheckersPlayer.PLAYER1):
                        # White Chess King
                        board_message += '♔'
                    elif (cell.token is CheckersTokenType.REGULAR and
                          cell.player is CheckersPlayer.PLAYER2):
                        # Bold Circled Bullet
                        board_message += underline + '⦿' + reset_underline
                    elif (cell.token is CheckersTokenType.KING and
                          cell.player is CheckersPlayer.PLAYER2):
                        # Black Chess King
                        board_message += '♚'
                    board_message += cell_padding

        return board_message + '```'

    def get_valid_moves(
      self, player: CheckersPlayer, repeated_capture: bool = False,
      force: bool = False
    ) -> dict[CheckersBoardPosition, set[tuple[bool, CheckersBoardPosition]]]:
        if self._valid_moves is not None and not force:
            return self._valid_moves

        self._valid_moves = {}

        for row in range(board_size):
            for column in range(board_size):
                cell: CheckersBoardCell = self.board[row][column]
                valid_moves: set[CheckersBoardPosition] = set()

                if cell.player is not player:
                    continue

                can_move_up:   bool = cell.can_move_up()
                can_move_down: bool = cell.can_move_down()

                # Up and left
                if can_move_up and row > 0 and column > 0:
                    next_cell: CheckersBoardCell = (
                        self.board[row - 1][column - 1]
                    )
                    if next_cell.token is CheckersTokenType.EMPTY:
                        if not repeated_capture:
                            valid_moves.add(
                              (False, CheckersBoardPosition(row - 1, column - 1))
                            )
                    elif next_cell.player is not player and row > 1 and column > 1:
                        next_cell = self.board[row - 2][column - 2]
                        if next_cell.token is CheckersTokenType.EMPTY:
                            valid_moves.add(
                              (True, CheckersBoardPosition(row - 2, column - 2))
                            )

                # Up and right
                if can_move_up and row > 0 and column < board_size - 1:
                    next_cell: CheckersBoardCell = (
                        self.board[row - 1][column + 1]
                    )
                    if next_cell.token is CheckersTokenType.EMPTY:
                        if not repeated_capture:
                            valid_moves.add(
                              (False, CheckersBoardPosition(row - 1, column + 1))
                            )
                    elif next_cell.player is not player and row > 1 and column < board_size - 2:
                        next_cell = self.board[row - 2][column + 2]
                        if next_cell.token is CheckersTokenType.EMPTY:
                            valid_moves.add(
                              (True, CheckersBoardPosition(row - 2, column + 2))
                            )

                # Down and left
                if can_move_down and row < board_size - 1 and column > 0:
                    next_cell: CheckersBoardCell = (
                        self.board[row + 1][column - 1]
                    )
                    if next_cell.token is CheckersTokenType.EMPTY:
                        if not repeated_capture:
                            valid_moves.add(
                              (False, CheckersBoardPosition(row + 1, column - 1))
                            )
                    elif next_cell.player is not player and row < board_size - 2 and column > 1:
                        next_cell = self.board[row + 2][column - 2]
                        if next_cell.token is CheckersTokenType.EMPTY:
                            valid_moves.add(
                              (True, CheckersBoardPosition(row + 2, column - 2))
                            )

                # Down and right
                if can_move_down and row < board_size - 1 and column < board_size - 1:
                    next_cell: CheckersBoardCell = (
                        self.board[row + 1][column + 1]
                    )
                    if next_cell.token is CheckersTokenType.EMPTY:
                        if not repeated_capture:
                            valid_moves.add(
                              (False, CheckersBoardPosition(row + 1, column + 1))
                            )
                    elif next_cell.player is not player and row < board_size - 2 and column < board_size - 2:
                        next_cell = self.board[row + 2][column + 2]
                        if next_cell.token is CheckersTokenType.EMPTY:
                            valid_moves.add(
                              (True, CheckersBoardPosition(row + 2, column + 2))
                            )

                if len(valid_moves) > 0:
                    self._valid_moves[CheckersBoardPosition(row, column)] = valid_moves

        return self._valid_moves


class CheckersGame(TextGuessGame):
    message: Optional[Message] = None
    user_id: Snowflake
    challengee_id: Snowflake
    legacy: bool

    in_thread: bool = False

    screen: 'CheckersScreen'
    board: CheckersBoard
    status = CheckersGameStatus.STARTED
    player = CheckersPlayer.PLAYER1
    repeated_capture: bool = False
    user_lost_token_count: int = 0
    challengee_lost_token_count: int = 0

    _last_token: Optional[CheckersBoardPosition] = None
    _last_target: Optional[CheckersBoardPosition] = None
    _last_captured: Optional[CheckersBoardPosition] = None
    _last_captured_type: Optional[CheckersTokenType] = None
    _last_input_method: Optional[CheckersInputMethod] = None

    def __init__(
      self, user_id: Snowflake, challengee_id: Snowflake, legacy: bool,
      screen: 'CheckersScreen'
    ):
        super().__init__(user_id, True)

        self.user_id = user_id
        self.challengee_id = challengee_id
        self.legacy = legacy
        self.screen = screen
        self.board = CheckersBoard()

    # TODO: Report already made moves
    def add_guess(self, user_id: Snowflake, guess: str) -> GuessOutcome:
        """(Un)Flags or Reveals the guessed cell and reports any issues."""
        if self.message is None:
            return GuessOutcome.Invalid

        match self.player:
            case CheckersPlayer.PLAYER1:
                if user_id != self.user_id:
                    return GuessOutcome.Invalid
            case CheckersPlayer.PLAYER2:
                if user_id != self.challengee_id:
                    return GuessOutcome.Invalid

        regex: str = r'^\s*([a-h][1-8])\s*,\s*([a-h][1-8])\s*$'
        guess_matches: Optional[Match[str]] = search(regex, guess, IGNORECASE)
        if not guess_matches:
            return GuessOutcome.Invalid
        guess_groups: tuple[str, ...] = guess_matches.groups()

        token_column: int = ord(guess_groups[0][0].upper()) - ord('A')
        token_row: int = board_size - int(guess_groups[0][1])
        token = CheckersBoardPosition(token_row, token_column)

        target_column: int = ord(guess_groups[1][0].upper()) - ord('A')
        target_row: int = board_size - int(guess_groups[1][1])
        target = CheckersBoardPosition(target_row, target_column)
        non_capture_target_info: tuple[bool, CheckersBoardPosition] = (
          False, target
        )
        capture_target_info: tuple[bool, CheckersBoardPosition] = (
          True, target
        )

        valid_moves: dict[CheckersBoardPosition, set[tuple[bool, CheckersBoardPosition]]] = (
          self.board.get_valid_moves(self.player, self.repeated_capture)
        )
        if token not in valid_moves or (
          non_capture_target_info not in valid_moves[token] and
          capture_target_info not in valid_moves[token]
        ):
            return GuessOutcome.Invalid

        self.make_move(token, target, CheckersInputMethod.REPLY)
        self.screen.stage = CheckersScreenStage.TOKEN
        create_task(self.screen.show_buttons())
        return GuessOutcome.Valid

    def __str__(self) -> str:
        user_mention = f'<@{self.user_id}>'
        challengee_mention = f'<@{self.challengee_id}>'

        # line 1
        status = f'{challengee_mention} You have been challenged to Checkers!\n'

        # line 2
        status += f'Blue is {user_mention}, red is {challengee_mention}.\n'

        # line 3
        status += 'Play using either the buttons below or by '
        if self.in_thread:
            status += 'sending'
        else:
            status += 'replying with'
        status += ' a message like C5, D4 to move a token to a new position.\n'

        # line 4
        status += '\n'

        # line 5
        status += f'It is currently '
        match self.player:
            case CheckersPlayer.PLAYER1:
                status += user_mention
            case CheckersPlayer.PLAYER2:
                status += challengee_mention
        status += "'s turn.\n"

        # lines 6(optional)
        if (self._last_token is not None and self._last_target is not None
              and self._last_input_method is not None):
            status += 'The last move by '

            # self.make_move moved the cell from token to target so using target position
            moved_cell: CheckersBoardCell = (
              self.board.board[self._last_target.row][self._last_target.column]
            )
            match moved_cell.player:
                case CheckersPlayer.PLAYER1:
                    status += user_mention
                case CheckersPlayer.PLAYER2:
                    status += challengee_mention

            status += ' was to move a '

            match moved_cell.token:
                case CheckersTokenType.REGULAR:
                    status += 'token'
                case CheckersTokenType.KING:
                    status += 'king'

            status += f' from {self._last_token} to {self._last_target}'

            if self._last_captured is not None and self._last_captured_type:
                status += ' and capture the '

                match self._last_captured_type:
                    case CheckersTokenType.REGULAR:
                        status += 'token'
                    case CheckersTokenType.KING:
                        status += 'king'

                status += f' at {self._last_captured}'

            status += f' via '

            match self._last_input_method:
                case CheckersInputMethod.SCREEN:
                    status += 'the buttons'
                case CheckersInputMethod.REPLY:
                    status += 'reply'
            status += '.\n'

        # line 7(optional)
        if self.user_lost_token_count > 0:
            status += f'{user_mention} has lost {self.user_lost_token_count} '
            status += 'token(s)'
        if self.challengee_lost_token_count > 0:
            if self.user_lost_token_count > 0:
                status += ', '
            status += f'{challengee_mention} has lost '
            status += f'{self.challengee_lost_token_count} token(s)'
        if (
          self.user_lost_token_count > 0 or
          self.challengee_lost_token_count > 0
        ):
            status += '.\n'

        status += self.board.get_board(
          self.screen.stage, self.screen.token, self.legacy
        )

        match self.status:
            case CheckersGameStatus.PLAYER1_WON:
                status += f'\n{user_mention} has won the game!'
            case CheckersGameStatus.PLAYER2_WON:
                status += f'\n{challengee_mention} has won the game!'
            case CheckersGameStatus.STARTED:
                pass

        if (self.message is not None
              and self.status is not CheckersGameStatus.STARTED):
            remove_game(self.message.id)
            remove_game(self.message.channel_id)

        return status

    def make_move(
      self, token: CheckersBoardPosition, target: CheckersBoardPosition,
      input_method: CheckersInputMethod
    ) -> None:
        if token.row >= board_size or token.column >= board_size:
            return
        if target.row >= board_size or target.column >= board_size:
            return

        # Find info on current token location
        token_cell: CheckersBoardCell = self.board.board[token.row][token.column]
        if token_cell.token is CheckersTokenType.EMPTY or token_cell.player is not self.player:
            return

        # Find into on target location
        target_cell: CheckersBoardCell = self.board.board[target.row][target.column]
        if target_cell.token is not CheckersTokenType.EMPTY:
            return

        # Backup move for printing
        self._last_token = token
        self._last_target = target
        self._last_input_method = input_method

        # Determine if move captures an opposing token
        # (x + x + n) % 2 = (2x + n) % 2 = (2x % 2 + n % 2) % 2 = (n % 2) % 2 = n % 2
        capturing: bool = (token.row + target.row) % 2 == 0

        # Remove captured token(if any) and backup token for printing
        if capturing:
            self._last_captured = CheckersBoardPosition(
              (token.row + target.row) // 2, (token.column + target.column) // 2
            )
            captured_cell: CheckersBoardCell = (
              self.board.board[self._last_captured.row][self._last_captured.column]
            )
            self._last_captured_type = captured_cell.token
            captured_cell.token = CheckersTokenType.EMPTY
            captured_cell.player = None
        else:
            self._last_captured = None
            self._last_captured_type = None

        # Move token to target position
        target_cell.token = token_cell.token
        target_cell.player = token_cell.player
        token_cell.token = CheckersTokenType.EMPTY
        token_cell.player = None

        # Check for forced additional captures
        if capturing:
            valid_moves: dict[CheckersBoardPosition, set[tuple[bool, CheckersBoardPosition]]] = (
                self.board.get_valid_moves(self.player, True, True)
            )

            self.repeated_capture = (
              target in valid_moves and
              len([move for move in valid_moves[target] if move[0]]) > 0
            )
        else:
            self.repeated_capture = False

        # Check for king promotion, count lost tokens and switch player if no forced captures
        match self.player:
            case CheckersPlayer.PLAYER1:
                if target.row == 0:
                    target_cell.token = CheckersTokenType.KING
                if capturing:
                    self.challengee_lost_token_count += 1
                if not self.repeated_capture:
                    self.player = CheckersPlayer.PLAYER2
            case CheckersPlayer.PLAYER2:
                if target.row == board_size - 1:
                    target_cell.token = CheckersTokenType.KING
                if capturing:
                    self.user_lost_token_count += 1
                if not self.repeated_capture:
                    self.player = CheckersPlayer.PLAYER1

        # End game if no remaining moves
        valid_moves: dict[CheckersBoardPosition, set[tuple[bool, CheckersBoardPosition]]] = (
          self.board.get_valid_moves(self.player, self.repeated_capture, True)
        )
        if len(valid_moves) == 0:
            match self.player:
                case CheckersPlayer.PLAYER1:
                    self.status = CheckersGameStatus.PLAYER1_WON
                case CheckersPlayer.PLAYER2:
                    self.status = CheckersGameStatus.PLAYER2_WON

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


# TODO: Allow going from target selection back to token selection
class CheckersScreen(Screen):
    created_initial_buttons = False

    game: CheckersGame
    stage = CheckersScreenStage.TOKEN
    token: Optional[CheckersBoardPosition] = None

    def __init__(
      self, menu: Menu, user_id: Snowflake, challengee_id: Snowflake,
      legacy: bool
    ):
        super().__init__(menu)
        self.game = CheckersGame(user_id, challengee_id, legacy, self)

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
        match self.stage:
          case CheckersScreenStage.TOKEN:
              await self.show_token_buttons()
          case CheckersScreenStage.TARGET:
              await self.show_target_buttons()
        await self.reload()

    async def show_token_buttons(self) -> None:
        valid_moves: dict[CheckersBoardPosition, set[tuple[bool, CheckersBoardPosition]]] = (
            self.game.board.get_valid_moves(self.game.player, self.game.repeated_capture)
        )

        token: CheckersBoardPosition
        for token in valid_moves:
            self.menu.add_item(create_button(str(token), self.token_pressed))  # pyright: ignore [reportArgumentType]

    async def show_target_buttons(self) -> None:
        valid_moves: dict[CheckersBoardPosition, set[tuple[bool, CheckersBoardPosition]]] = (
            self.game.board.get_valid_moves(self.game.player, self.game.repeated_capture)
        )

        target: CheckersBoardPosition
        for _, target in valid_moves[self.token]:
            self.menu.add_item(create_button(str(target), self.target_pressed))  # pyright: ignore [reportArgumentType]

        self.menu.add_item(create_button("Back", self.back_pressed))

    async def token_pressed(
      self, ctx: ViewContext, button: ScreenButton
    ) -> None:
        if button.label is None:
            return
        if self.game.player is CheckersPlayer.PLAYER1 and ctx.user.id != self.game.user_id:
            return
        if self.game.player is CheckersPlayer.PLAYER2 and ctx.user.id != self.game.challengee_id:
            return

        column = ord(button.label[0]) - ord('A')
        row = board_size - int(button.label[1])
        self.token = CheckersBoardPosition(row, column)
        self.stage = CheckersScreenStage.TARGET
        
        await self.show_buttons()

    async def target_pressed(
      self, ctx: ViewContext, button: ScreenButton
    ) -> None:
        if button.label is None:
            return
        if self.game.player is CheckersPlayer.PLAYER1 and ctx.user.id != self.game.user_id:
            return
        if self.game.player is CheckersPlayer.PLAYER2 and ctx.user.id != self.game.challengee_id:
            return

        column = ord(button.label[0]) - ord('A')
        row = board_size - int(button.label[1])
        target = CheckersBoardPosition(row, column)
        self.stage = CheckersScreenStage.TOKEN

        self.game.make_move(self.token, target, CheckersInputMethod.SCREEN)

        await self.show_buttons()

    async def back_pressed(
      self, ctx: ViewContext, button: ScreenButton
    ) -> None:
        self.stage = CheckersScreenStage.TOKEN

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

    user = option(User, 'User to challenge')
    legacy = option(bool, 'Support legacy mobile devices', default=False)

    thread = option(bool, 'Automatically create a thread', default=False)

    async def callback(self, ctx: Context) -> None:
        """Handle checkers command being run by showing board and buttons."""
        logger.info(
          f'{ctx.user} is starting a game(user: {self.user}, ' +
          f'legacy: {self.legacy}, thread: {self.thread})'
        )

        checkers_menu = Menu()
        screen = CheckersScreen(
          checkers_menu, ctx.user.id, self.user.id, self.legacy
        )

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
