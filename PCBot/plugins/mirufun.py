import crescent
import hikari
import miru
from miru.ext import menu
from typing import Optional

# TODO: Find a way to access the root screen without using _stack

plugin = crescent.Plugin[hikari.GatewayBot, None]()

grid_size = 10

class NumberScreen(menu.Screen):
    flag: bool
    letter: chr

    def __init__(self, menu: menu.Menu, flag: bool, letter: chr) -> None:
          super().__init__(menu)
          self.flag = flag
          self.letter = letter
  
    async def build_content(self) -> menu.ScreenContent:
        return menu.ScreenContent(
            embed=hikari.Embed(
              title=f'Select row for {"flag" if self.flag else "clear"}',
            ),
        )
    
    @menu.button(label='Back', custom_id='back',
                 style=hikari.ButtonStyle.SECONDARY)
    async def back(self, ctx: miru.ViewContext,
                   button: menu.ScreenButton) -> None:
        await self.menu.pop()

class NumberButton(menu.ScreenButton):
    number: int

    def __init__(self, number: int) -> None:
        """Create a button with a number label."""
        self.number = number
        super().__init__(
          label=str(number + 1)
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        menu = self.menu
        menu._stack[0].previous_selection =\
          f'{self.screen.letter}{self.number + 1}'
        await menu.pop_until_root()

def create_number_screen(miru_menu: menu.Menu, flag: bool, letter: chr) -> menu.Screen:
    number_screen = NumberScreen(miru_menu, flag, letter)
    back_button = number_screen.get_item_by_id('back')
    number_screen.remove_item(back_button)
    for i in range(grid_size):
        number_screen.add_item(NumberButton(i))
    number_screen.add_item(back_button)
    return number_screen


class LetterScreen(menu.Screen):
    flag: bool

    def __init__(self, menu: menu.Menu, flag: bool) -> None:
          super().__init__(menu)
          self.flag = flag
  
    async def build_content(self) -> menu.ScreenContent:
        return menu.ScreenContent(
            embed=hikari.Embed(
              title=f'Select column for {"flag" if self.flag else "clear"}',
            ),
        )
    
    @menu.button(label='Back', custom_id='back',
                 style=hikari.ButtonStyle.SECONDARY)
    async def back(self, ctx: miru.ViewContext,
                   button: menu.ScreenButton) -> None:
        await self.menu.pop()

class LetterButton(menu.ScreenButton):
    letter: chr

    def __init__(self, letter_number: int) -> None:
        """Create a button with a captial letter label."""
        self.letter = chr(letter_number + ord('A'))
        super().__init__(
          label=str(self.letter)
        )

    async def callback(self, ctx: miru.ViewContext) -> None:
        await self.menu.push(create_number_screen(self.menu, self.screen.flag, self.letter))

def create_letter_screen(miru_menu: menu.Menu, flag: bool) -> menu.Screen:
    letter_screen = LetterScreen(miru_menu, flag)
    back_button = letter_screen.get_item_by_id('back')
    letter_screen.remove_item(back_button)
    for i in range(grid_size):
        letter_screen.add_item(LetterButton(i))
    letter_screen.add_item(back_button)
    return letter_screen


class PredictionScreen(menu.Screen):
    previous_selection: Optional[str] = None

    async def build_content(self) -> menu.ScreenContent:
        embed = hikari.Embed(title='Start Prediction')
        if self.previous_selection is not None:
            embed.description = f'Previous prediction was {self.previous_selection}'
        return menu.ScreenContent(embed=embed)

    @menu.button(label="Bomb")
    async def bomb(self, ctx: miru.ViewContext,
                   button: menu.ScreenButton) -> None:
        await self.menu.push(create_letter_screen(self.menu, True))

    @menu.button(label="Not Bomb")
    async def not_bomb(self, ctx: miru.ViewContext,
                   button: menu.ScreenButton) -> None:
        await self.menu.push(create_letter_screen(self.menu, False))

@plugin.include
@crescent.command(name='mirufun')
class SomeSlashCommand:
    async def callback(self, ctx: crescent.Context) -> None:
        my_menu = menu.Menu() # Create a new Menu
        screen = PredictionScreen(my_menu)
        
        # Pass in the initial screen
        builder = await my_menu.build_response_async(plugin.model.miru, screen)
        await ctx.respond_with_builder(builder)
        plugin.model.miru.start_view(my_menu)

#@plugin.include
#@crescent.command(name='mirufun')
#class SomeSlashCommand:
#    async def callback(self, ctx: crescent.Context) -> None:
#        page1 = nav.Page(
#           content='test'
#        )
#        
#        page2 = nav.Page(
#           content='test'
#        )
#        
#        # The list of pages this navigator should paginate through
#        # This should be a list that contains
#        # 'str', 'hikari.Embed', or 'nav.Page' objects.
#        pages = [page1, page2]
#
#        # Define our navigator and pass in our list of pages
#        navigator = nav.NavigatorView(pages=pages)
#
#
#        for i in range(20):
#          print(i)
#          navigator.add_item(nav.NavButton(
#            label=f'test {i}'
#          ))
#
#        builder = await navigator.build_response_async(plugin.model.miru)
#        await ctx.respond_with_builder(builder)
#        plugin.model.miru.start_view(navigator)
