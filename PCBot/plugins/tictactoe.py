"""This module contains the bot's tictactoe minigame command."""

import crescent
import hikari
import miru
import re
from crescent.ext import docstrings
from enum import Enum
from PCBot.botdata import BotData
from typing import Optional

# TODO: Disable buttons on timeout
# TODO: Disable buttons when the bot shuts down, does reload also break views?
# TODO: Add option to change starting player. Have random option?
# TODO: Support larger grid sizes
# TODO: Support more players?
#      The win detector can support it, just not sure if it works gameplay wise

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()


class Player(Enum):
    """Enum to store the different players."""

    Challenger  = 0
    Challengee1 = 1
    Challengee2 = 2


player_styles = [
  hikari.ButtonStyle.PRIMARY,  # Blue
  hikari.ButtonStyle.DANGER,   # Red
  hikari.ButtonStyle.SUCCESS   # Green
]

# Gray
default_style = hikari.ButtonStyle.SECONDARY


class TicTacToeView(miru.View):
    """Miri view with buttons to show the state and allow user selection."""

    players: list[hikari.User]
    current_player: Player

    grid_size: int

    def __init__(self, challenger: hikari.User, challengee: hikari.User,
                 challengee2: Optional[hikari.User], grid_size: int) -> None:
        """Create view and buttons to manage tic tac toe game."""
        super().__init__()
        self.players = [challenger, challengee]
        if challengee2 is not None:
            self.players.append(challengee2)
        # This is arbitrary
        self.current_player = Player.Challenger
        self.grid_size = grid_size
        for cell_value in range(grid_size * grid_size):
            self.add_item(TicTacToeButton(cell_value, grid_size))

    # From https://stackoverflow.com/a/39923094
    def check_rows(self, board: list[list[hikari.ButtonStyle]])\
    -> Optional[hikari.ButtonStyle]:
        """Check if a player has board size pieces in row."""
        for row in board:
            if len(set(row)) == 1 and row[0] != default_style:
                return row[0]
        return None

    def check_diagonals(self, board: list[list[hikari.ButtonStyle]])\
    -> Optional[hikari.ButtonStyle]:
        """Check if a player has board size pieces along a diagonal."""
        if (len(set([board[i][i] for i in range(len(board))])) == 1 and
             board[0][0] != default_style):
            return board[0][0]
        if len(set([
                      board[i][len(board)-i-1]
                      for i in range(len(board))
                   ])) == 1 and board[0][len(board)-1] != default_style:
            return board[0][len(board)-1]
        return None

    def check_win(self, board: list[list[hikari.ButtonStyle]])\
    -> Optional[hikari.ButtonStyle]:
        """Check if a player has won the game."""
        # Transpose to check rows, then columns
        for new_board in [board, list(zip(*board))]:
            result = self.check_rows(new_board)
            if result is not None:
                return result
        # Otherwise check diagonals
        return self.check_diagonals(board)

    def check_draw(self) -> bool:
        """Check for a draw by checking if all cells are taken."""
        for child in self.children:
            if child.style == default_style:
                return False
        return True

    def produce_board(self) -> list[list[hikari.ButtonStyle]]:
        """Convert the board into a grid for check_win and co."""
        grid: list[list[hikari.ButtonStyle]] = []
        row: Optional[list[hikari.ButtonStyle]] = None
        row_num = -1
        for child in self.children:
            if child.cell_number // self.grid_size != row_num:
                if row is not None:
                    grid.append(row)
                row = []
                row_num = child.cell_number // self.grid_size
            row.append(child.style)
        grid.append(row)
        return grid

    async def determine_winner(self, ctx: miru.ViewContext) -> bool:
        """Determine if the game has finished and if so who won."""
        # Check for winner
        board = self.produce_board()
        winner_style = self.check_win(board)
        # This should not happen but I want to see if it ever does
        if winner_style == default_style:
            print(winner_style)
            print(board)
        draw = self.check_draw()
        if not draw and winner_style not in player_styles:
            return False

        # Disable interaction
        for child in self.children:
            child.disabled = True

        # Report game over
        message = ctx.message.content
        if draw:
            new_final_line = 'The game was a draw.'
        else:
            new_final_line = f'{ctx.user.mention} is the winner!'
        updated_message = re.sub(r"It is currently <@\d+>'s turn.",
                                 new_final_line, message, 1)
        await ctx.edit_response(updated_message, components=self)
        self.stop()
        return True

    async def view_check(self, ctx: miru.ViewContext) -> bool:
        """Before calling button methods check if presser is current player."""
        return ctx.user.username == self.players[self.current_player.value].username


class TicTacToeButton(miru.Button):
    """Create, style and handle presses for tic tac toe grid buttons."""

    cell_number: int

    def __init__(self, cell_number: int, grid_size: int) -> None:
        """Create and initally style a button."""
        super().__init__(
          label=str(cell_number + 1), row=cell_number // grid_size,
          style=default_style
        )
        self.cell_number = cell_number

    async def callback(self, ctx: miru.ViewContext) -> None:
        """Respond to button presses by restyling the button."""
        # Prepare changes to button
        self.style = player_styles[self.view.current_player.value]
        new_player_index =\
          (self.view.current_player.value + 1) % len(self.view.players)
        self.view.current_player = Player(new_player_index)
        self.disabled = True

        # Check for winner, this must be after button changes so that the most
        # recent button press counts and is shown on the grid
        game_over = await self.view.determine_winner(ctx)
        if game_over:
            return

        # Prepare modified message with new current player mention
        message = ctx.message.content
        new_mention = self.view.players[new_player_index].mention + "'"
        updated_message = re.sub(r"<@\d+>'", new_mention, message, 1)

        # Update game message
        await ctx.edit_response(updated_message, components=self.view)


@plugin.include
@docstrings.parse_doc
@crescent.command(name='tictactoe', dm_enabled=False)
class TicTacToeCommand:
    """
    Challenge a user to tic tac toe.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).

    Args:
        user: User to challenge.
    """

    user = crescent.option(hikari.User)
    allow_experimental = crescent.option(
        bool, 'Allow the use of experimental settings',
        default=False
    )
    experimental_grid_size = crescent.option(int, default=3,
                                             min_value=2, max_value=5)
    experimental_third_player = crescent.option(hikari.User, default=None)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle tictactoe command being run by showing button grid view."""
        mention_line = self.user.user.mention
        title_prefix = ''
        colour_line_suffix = ''
        if self.allow_experimental:
            if self.experimental_third_player is not None:
                challengee2 = self.experimental_third_player.user
                mention_line += f' {challengee2.mention}'
                colour_line_suffix += f', green is {challengee2.mention}'
            else:
                challengee2 = None
            view = TicTacToeView(
                challenger=ctx.user, challengee=self.user.user,
                challengee2=challengee2, grid_size=self.experimental_grid_size
            )
            title_prefix += 'experimental'
        else:
            view = TicTacToeView(
                challenger=ctx.user, challengee=self.user.user,
                challengee2=None, grid_size=3
            )
        await ctx.respond(
          mention_line +
          f' You have been challenged to {title_prefix} Tic Tac Toe!\n'
          f'Blue is {ctx.user.mention}, red is {self.user.user.mention}'
          f'{colour_line_suffix}.\n'
          'It is currently '
          f"{view.players[view.current_player.value].mention}'s turn.\n",
          components=view
        )
        plugin.model.miru.start_view(view)
