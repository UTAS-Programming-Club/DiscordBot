"""This module contains the bot's tower of hanoi minigame command."""
# pyright: strict

# TODO: Report mistakes

from crescent import command, Context, option, Plugin
from hikari import GatewayBot, Message, Snowflake
from logging import getLogger, Logger
from typing import Final, Optional
from PCBot.core.replyhandler import (
  GuessOutcome, remove_game, send_text_message, TextGuessGame
)

logger: Logger = getLogger(__name__)
plugin = Plugin[GatewayBot, None]()

stack_count: Final[int] = 3
disk_count: Final[int] = 4


class HanoiGame(TextGuessGame):
    """Maintain and allow moves for a tower of hanoi game."""

    message: Optional[Message] = None
    in_thread: bool = False

    grid: Final[list[list[int]]]

    def __init__(self, user_id: Snowflake, multiguesser: bool):
        """Start a tower of hanoi game."""
        super().__init__(user_id, multiguesser)

        # TODO: Use minesweeper record style grid instead of this
        self.grid = [
          [0 for _ in range(disk_count)] for _ in range(stack_count)
        ]
        self.grid[0] = [i + 1 for i in range(disk_count)]
        logger.info(self.grid)

    def _find_top(self, stack: int) -> int:
        """Find index of top disk on stack."""
        for disk in range(disk_count):
            if self.grid[stack][disk] != 0:
                return disk
        return disk_count

    def _check_win(self) -> bool:
        """Check if the game is over."""
        # First stack is initial stack so cannot win on it
        logger.info(self.grid)
        for stack in range(1, stack_count):
            value: int = 0
            for disk in range(disk_count):
                if self.grid[stack][disk] == value + 1:
                    value += 1
                else:
                    break
            logger.info(f'Test: {value}')
            if value == disk_count:
                return True
        return False

    def add_guess(self, user_id: Snowflake, guess: str) -> GuessOutcome:
        """Perform a move and reports any issues."""
        digits: list[int] = [int(c) for c in guess if c.isdigit()]
        if len(digits) != 2:
            logger.info(f'Invalid input: {guess}')
            return GuessOutcome.Invalid

        source_stack: int = digits[0] - 1
        dest_stack: int = digits[1] - 1
        if source_stack == dest_stack:
            logger.info('Source and dest stacks match')
            return GuessOutcome.Invalid
        if source_stack >= disk_count or dest_stack >= disk_count:
            logger.info('Source or dest stack too high')
            return GuessOutcome.Invalid

        source_disk: int = self._find_top(source_stack)
        dest_disk: int = self._find_top(dest_stack)
        if (
          dest_disk != disk_count
          and self.grid[dest_stack][dest_disk] <
          self.grid[source_stack][source_disk]
        ):
            logger.info(f'Invalid target: ({dest_stack}, {dest_disk})')
            return GuessOutcome.Invalid

        # Place source disk above destination stack's top most disk
        dest_disk -= 1

        self.grid[source_stack][source_disk], \
            self.grid[dest_stack][dest_disk] \
            = self.grid[dest_stack][dest_disk], \
            self.grid[source_stack][source_disk]
        logger.info(digits)
        logger.info(source_disk)
        logger.info(dest_disk)

        return GuessOutcome.Valid

    def __str__(self) -> str:
        """Produce a string to describe the current state of the game."""
        # line 1
        status = 'You are playing Tower of Hanoi.\n'

        # line 2
        status += 'Play by '
        if self.in_thread:
            status += 'sending'
        else:
            status += 'replying with'
        status += ' a message like 1, 2 to move a ring.\n'

        # line 3
        status += '\n'

        # lines 4 to 4 + stack
        status += '```'

        for disk in range(-1, disk_count):
            status += ' '
            for stack in range(stack_count):
                value: int = self.grid[stack][disk] if disk >= 0 else 0
                char: str = '|' if value == 0 else str(value)
                status += f'{char} '
            status += '\n'

        # Technically on next line but appears innocuous
        status += '```'

        # TODO: Cache win status?
        if self.message is not None and self._check_win():
            status += '\nYou win!'
            remove_game(self.message.id)
            remove_game(self.message.channel_id)

        return status


@plugin.include
@command(name='hanoi', description='Play a game of Tower of Hanoi.')
class HanoiCommand:
    """Reply handler based command to handle tower of hanoi game requests."""

    extra_description = """
    Requested by Joshua(somethingsensible).
    Implemented by Joshua(somethingsensible).
    """

    multiguesser = option(bool, 'Allow anyone to play', default=False)
    thread = option(bool, 'Automatically create a thread', default=False)

    async def callback(self, ctx: Context) -> None:
        """Handle tower of hanoi command being run by showing the towers."""
        game = HanoiGame(ctx.user.id, self.multiguesser)
        await send_text_message(ctx, self.thread, 'hanoi', game)
