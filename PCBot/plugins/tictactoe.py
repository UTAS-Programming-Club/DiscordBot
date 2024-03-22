"""This module contains the bot's tictactoe minigame command."""

import crescent
import hikari
import miru
import re
from crescent.ext import docstrings
from PCBot.botdata import BotData
from typing import Optional

# TODO: Disable buttons on timeout
# TODO: Disable buttons when the bot shuts down, does reload also break views?
# TODO: Support larger grid sizes
# TODO: Support more players?
#      The win detector can support it, just not sure if it works gameplay wise

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()

# Blue
challenger_style = hikari.ButtonStyle.PRIMARY
# Red
challengee_style = hikari.ButtonStyle.DANGER
# Gray
default_style = hikari.ButtonStyle.SECONDARY


class TicTacToeView(miru.View):
    """Miri view with buttons to show the state and allow user selection."""

    challenger: hikari.User
    challengee: hikari.User
    current_player: hikari.User

    def __init__(self, challenger: hikari.User, challengee: hikari.User)\
    -> None:
        """Create view and buttons to manage tic tac toe game."""
        super().__init__()
        self.challenger = challenger
        self.challengee = challengee
        # This is arbitrary
        self.current_player = self.challenger
        for cell_value in range(9):
            self.add_item(TicTacToeButton(cell_value))

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
        """Check if a player has board size peices along a diagonal."""
        if len(set([board[i][i] for i in range(len(board))])) == 1:
            return board[0][0]
        if len(set([
                      board[i][len(board)-i-1]
                      for i in range(len(board))
                   ])) == 1:
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

    def produce_board(self) -> list[list[hikari.ButtonStyle]]:
        """Convert the board into a grid for check_win and co."""
        grid: list[list[hikari.ButtonStyle]] = []
        row: Optional[list[hikari.ButtonStyle]] = None
        row_num = -1
        for child in self.children:
            if child.cell_number // 3 != row_num:
                if row is not None:
                    grid.append(row)
                row = []
                row_num = child.cell_number // 3
            row.append(child.style)
        grid.append(row)
        return grid

    async def determine_winner(self, ctx: miru.ViewContext) -> bool:
        """Determine if the game has finished and if so who won."""
        # Check for winner
        board = self.produce_board()
        winner_style = self.check_win(board)
        if (winner_style != challenger_style and
           winner_style != challengee_style):
            return False

        # Disable interaction
        for child in self.children:
            child.disabled = True

        # Report game over
        message = ctx.message.content
        new_mention = f'{ctx.user.mention} is the winner!'
        updated_message = re.sub(r"It is currently <@\d+>'s turn.",
                                 new_mention, message, 1)
        await ctx.edit_response(updated_message, components=self)
        self.stop()

    async def view_check(self, ctx: miru.ViewContext) -> bool:
        """Before calling button methods check if presser is current player."""
        return ctx.user.username == self.current_player.username


class TicTacToeButton(miru.Button):
    """Create, style and handle presses for tic tac toe grid buttons."""

    cell_number: int

    def __init__(self, cell_number: int) -> None:
        """Create and initally style a button."""
        super().__init__(
          label=str(cell_number + 1), row=cell_number // 3, style=default_style
        )
        self.cell_number = cell_number

    async def callback(self, ctx: miru.ViewContext) -> None:
        """Respond to button presses by restyling the button."""
        # Prepare changes to button
        if ctx.user.username == self.view.challenger.username:
            self.style = challengee_style
            self.view.current_player = self.view.challengee
        else:
            self.style = challenger_style
            self.view.current_player = self.view.challenger
        self.disabled = True

        # Prepare modified message with new current player mention
        message = ctx.message.content
        new_mention = self.view.current_player.mention + "'"
        updated_message = re.sub(r"<@\d+>'", new_mention, message, 1)

        # Update game message
        await ctx.edit_response(updated_message, components=self.view)

        # Check for winner, this must be after button changes so that the most
        # recent button press counts and is shown on the grid
        game_over = await self.view.determine_winner(ctx)
        if game_over:
            return


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

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle tictactoe command being run by showing button grid view."""
        view = TicTacToeView(challenger=ctx.user, challengee=self.user.user)
        await ctx.respond(
          f'{self.user.user.mention} '
          'You have been challenged to Tic Tac Toe!\n'
          f'Blue is {ctx.user.mention}, red is {self.user.user.mention}.\n'
          f"It is currently {view.current_player.mention}'s turn.\n",
          components=view
        )
        plugin.model.miru.start_view(view)
