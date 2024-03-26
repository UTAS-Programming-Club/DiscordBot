"""This module contains the bot's miru menu experimentation command."""

import crescent
import hikari
import miru
from miru.ext import menu
from typing import Optional

# TODO: Find a way to access the root screen without using _stack

plugin = crescent.Plugin[hikari.GatewayBot, None]()

grid_size = 10


class SelectionScreen(menu.Screen):
    """Miru screen which asks the user for a letter or number selction."""

    flag: bool
    letter: Optional[chr] = None

    def __init__(self, menu: menu.Menu, flag: bool,
                 letter: Optional[chr] = None) -> None:
        """Create an internal screen and store parameters for later use."""
        super().__init__(menu)
        self.flag = flag
        self.letter = letter

    async def build_content(self) -> menu.ScreenContent:
        """Create a visible screen using stored properties."""
        prediction_type = 'flag' if self.flag else 'clear'
        selection_type = 'column' if self.letter is None else 'row'
        return menu.ScreenContent(
            embed=hikari.Embed(
                title=f'Select {selection_type} for {prediction_type}'
            ),
        )

    @menu.button(label='Back', custom_id='back',
                 style=hikari.ButtonStyle.SECONDARY)
    async def back(self, ctx: miru.ViewContext,
                   button: menu.ScreenButton) -> None:
        """Miru button to restore the previous screen."""
        await self.menu.pop()


class NumberButton(menu.ScreenButton):
    """Miru screen button that displays a provided number."""

    number: int

    def __init__(self, number: int) -> None:
        """Create a button with a number label."""
        self.number = number
        super().__init__(
          label=str(number + 1)
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        """Handle user pressing button by showing root with selected cell."""
        menu = self.menu
        menu._stack[0].previous_selection =\
          f'{self.screen.letter}{self.number + 1}'
        await menu.pop_until_root()


def create_number_screen(miru_menu: menu.Menu, flag: bool,
                         letter: chr) -> menu.Screen:
    """Create a SelectionScreen set up to take a number from the user."""
    number_screen = SelectionScreen(miru_menu, flag, letter)
    back_button = number_screen.get_item_by_id('back')
    number_screen.remove_item(back_button)
    for i in range(grid_size):
        number_screen.add_item(NumberButton(i))
    number_screen.add_item(back_button)
    return number_screen


class LetterButton(menu.ScreenButton):
    """Miru screen button that displays a provided letter."""

    letter: chr

    def __init__(self, letter_number: int) -> None:
        """Create a button with a captial letter label."""
        self.letter = chr(letter_number + ord('A'))
        super().__init__(
          label=str(self.letter)
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        """Handle user pressing button by showing number selection screen."""
        number_screen = create_number_screen(self.menu, self.screen.flag,
                                             self.letter)
        await self.menu.push(number_screen)


def create_letter_screen(miru_menu: menu.Menu, flag: bool) -> menu.Screen:
    """Create a SelectionScreen set up to take a letter from the user."""
    letter_screen = SelectionScreen(miru_menu, flag)
    back_button = letter_screen.get_item_by_id('back')
    letter_screen.remove_item(back_button)
    for i in range(grid_size):
        letter_screen.add_item(LetterButton(i))
    letter_screen.add_item(back_button)
    return letter_screen


class PredictionScreen(menu.Screen):
    """Miru screen to asks the user what minesweeper prediction to make."""

    previous_selection: Optional[str] = None

    async def build_content(self) -> menu.ScreenContent:
        """Create a visible screen to show prediction option buttons."""
        embed = hikari.Embed(title='Start Prediction')
        if self.previous_selection is not None:
            embed.description =\
              f'Previous prediction was {self.previous_selection}'
        return menu.ScreenContent(embed=embed)

    @menu.button(label="Bomb")
    async def bomb(self, ctx: miru.ViewContext,
                   button: menu.ScreenButton) -> None:
        """Miru button to make a bomb prediction."""
        await self.menu.push(create_letter_screen(self.menu, True))

    @menu.button(label="Not Bomb")
    async def not_bomb(self, ctx: miru.ViewContext,
                       button: menu.ScreenButton) -> None:
        """Miru button to make a no bomb prediction."""
        await self.menu.push(create_letter_screen(self.menu, False))


@plugin.include
@crescent.command(name='mirufun')
class MiruFunCommand:
    """
    Test command to try out miru menus.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle mirufun command being run by showing prediction menu."""
        prediction_menu = menu.Menu()
        screen = PredictionScreen(prediction_menu)
        builder =\
          await prediction_menu.build_response_async(plugin.model.miru, screen)
        await ctx.respond_with_builder(builder)
        plugin.model.miru.start_view(prediction_menu)
