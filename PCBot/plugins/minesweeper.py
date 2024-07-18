"""This module contains the bot's minesweeper minigame command."""

import crescent
import hikari
import inspect
import miru
from crescent.ext import docstrings
from dataclasses import dataclass
from enum import Enum
from miru.ext import menu
from miru.ext.menu.items import button, DecoratedScreenItem
from PCBot.botdata import BotData
from typing import Awaitable, Callable, Optional

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()

class MinesweeperScreenStage(Enum):
    OPTION = 1
    LETTER = 2
    NUMBER = 3


class MinesweeperOption(Enum):
    FLAG   = 1
    REVEAL = 2


class MinesweeperInputMethod(Enum):
    SCREEN = 1
    REPLY  = 2


@dataclass
class MinesweeperGame:
    grid_size: int

    last_column: Optional[int] = None # Letter
    last_row: Optional[int] = None    # Number
    last_option: Optional[MinesweeperOption] = None
    last_input_method: Optional[MinesweeperInputMethod] = None

    def make_move(
      self, column: int, row: int, option: MinesweeperOption,
      input_method: MinesweeperInputMethod
    ) -> None:
        if column >= self.grid_size or row >= self.grid_size:
            return

        self.last_column = column
        self.last_row = row
        self.last_option = option
        self.last_input_method = input_method

    def get_current_status(self) -> str:
        status = inspect.cleandoc(
          '''You are playing minesweeper.
          Play using either the buttons below or by replying with a
          message like C7 to reveal a square or fB2 to flag instead.'''
        )

        if (self.last_column is not None and self.last_row is not None
            and self.last_option is not None
            and self.last_input_method is not None):
                status += '\n\nThe last move to was to '

                # TODO: Split into flag and unflag cases
                if self.last_option is MinesweeperOption.FLAG:
                    status += '(un)flag'
                elif self.last_option is MinesweeperOption.REVEAL:
                    status += 'reveal'
                else:
                    raise Exception(
                      f'Invalid input option {self.last_option} used.'
                    )

                last_column_letter = chr(ord('A') + self.last_column)
                status += f' cell {last_column_letter}{self.last_row} via '

                if self.last_input_method is MinesweeperInputMethod.SCREEN:
                    status += 'the buttons'
                elif self.last_input_method is MinesweeperInputMethod.REPLY:
                    status += 'reply'
                else:
                    raise Exception(
                      f'Invalid input method {self.last_input_method} used.'
                    )
                status += '.'
        
        return status


def create_button(
  label: str,
  callback: Callable[
    [menu.Screen, miru.ViewContext, menu.ScreenButton], Awaitable[None],
  ],
  style = hikari.ButtonStyle.PRIMARY
) -> menu.ScreenButton:
    button = menu.ScreenButton(label, style=style)
    button.callback = lambda ctx: callback(ctx, button)
    return button


class MinesweeperScreen(menu.Screen):
    created_initial_buttons = False

    state = MinesweeperScreenStage.OPTION
    option: Optional[MinesweeperOption] = None

    letter: Optional[chr] = None

    game: MinesweeperGame

    def __init__(self, menu: menu.Menu, grid_size: int):
        super().__init__(menu)
        self.game = MinesweeperGame(grid_size)

    async def build_content(self) -> menu.ScreenContent:
        if not self.created_initial_buttons:
          self.created_initial_buttons = True
          await self.show_option_buttons()

        return menu.ScreenContent(
          content=self.game.get_current_status()
        )

    async def show_option_buttons(self) -> None:
        self.menu.clear_items()
        self.menu.add_item(create_button('(Un)flag', self.flag_pressed))
        self.menu.add_item(create_button('Reveal', self.reveal_pressed))
        await self.menu.update_message(await self.build_content())

    async def show_input_buttons(self) -> None:
        self.menu.clear_items()

        for i in range(self.game.grid_size):
            if self.state == MinesweeperScreenStage.LETTER:
                label = str(chr(ord('A') + i))
            elif self.state == MinesweeperScreenStage.NUMBER:
                label = str(i)
            else:
                raise Exception(
                  f'Invalid state {self.state} found while updating buttons'
                )
            self.menu.add_item(create_button(f'{label}', self.input_pressed))

        self.menu.add_item(create_button(
          'Back', self.back_pressed, style=hikari.ButtonStyle.DANGER
        ))

        await self.menu.update_message(await self.build_content())

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
            number = int(button.label[0])
            self.game.make_move(
              self.letter, number, self.option, MinesweeperInputMethod.SCREEN
            )
            self.state = MinesweeperScreenStage.OPTION
            self.option = None
            self.letter = None
            await self.show_option_buttons()
        else:
            raise Exception(
              f'Input button pressed during state {self.state}'
            )


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
        int, 'Size of minesweeper grid', min_value=2, default=9, max_value=24
    )
    bomb_count = crescent.option(
        int, 'Number of bombs in the grid', min_value=1, default=5, max_value=80
    )

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle minesweeper command being run by showing grid and buttons."""
        minesweeper_menu = menu.Menu()
        screen = MinesweeperScreen(minesweeper_menu, self.grid_size)
        screen_builder = await minesweeper_menu.build_response_async(
            plugin.model.miru, screen
        )
        await ctx.respond_with_builder(screen_builder)
        plugin.model.miru.start_view(minesweeper_menu)
