"""This module contains the bot's rock paper scissors minigame command."""

import crescent
import hikari
import miru
from crescent.ext import docstrings
from enum import Enum
from PCBot.botdata import BotData
from typing import Optional

# TODO: Add a variant for more than 2 people
# TODO: Prevent users changing their pick
# TODO: Tell user when their pick has been received
# TODO: Report timeout
# TODO: Disable buttons visibly after the round is over or timeout has occurred
# TODO: Convert to user command or at least offer that option

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()

# Not useful for this as command options can be seen by users.
# Keeping as autocomplete may be useful for something else.
# async def rps_autocomplete_response(
#     ctx: crescent.AutocompleteContext,
#     option: hikari.AutocompleteInteractionOption
# ) -> list[tuple[str, str]]:
#     return
#
#
# async def fetch_rps_autocomplete_options(
#   ctx: crescent.AutocompleteContext,
#   option: hikari.AutocompleteInteractionOption
# ) -> list[tuple[str, str]]:
#     _options = await ctx.fetch_options()
#     return []

# Not useful as returning False from modal_check still closes the Modal.
# I was hoping that it would show an error and allow changing input.
# Keeping as it may be useful for something else.
# class RPSModal(miru.Modal, title='Rock Paper Scissors'):
#     pick = miru.TextInput(
#       label='Rock, Paper or Scissors',
#       required=True,
#       min_length=4,
#       max_length=8,
#     )
#
#     async def modal_check(self, ctx: miru.ModalContext) -> bool:
#         if ctx.values[self.pick].casefold() in ['rock', 'paper', 'scissors']:
#             return True
#         else:
#             await ctx.respond(
#               f'You entered "{ctx.values[self.pick]}" which is not allowed'
#             )
#             return False
#
#     # The callback function is called after the user hits 'Submit'
#     async def callback(self, ctx: miru.ModalContext) -> None:
#         # You can also access the values using ctx.values,
#         # Modal.values, or use ctx.get_value_by_id()
#         await ctx.respond(
#           f'You picked {self.pick.value}'
#         )
# Above is sent with:
# modal = RPSModal()
# builder = modal.build_response(plugin.model.miru)
# await ctx.respond_with_builder(builder)
# plugin.model.miru.start_modal(modal)


class RPSPick(Enum):
    """Enum to store each user's rock paper scissors selection."""

    Rock     = 0
    Paper    = 1
    Scissors = 2


class RPSView(miru.View):
    """Miri view with buttons to obtain each user's selection."""

    challenger: hikari.User
    challengee: hikari.User
    challenger_pick: Optional[RPSPick] = None
    challengee_pick: Optional[RPSPick] = None
    er_pick = 0
    ee_pick = 0

    message_emojis = ['\N{ROCK}', '\N{SCROLL}', '\N{BLACK SCISSORS}']

    async def determine_winner(self, ctx: miru.ViewContext) -> None:
        """Determine if the game has finished and if so who won."""
        if self.challenger_pick is None or self.challengee_pick is None:
            return
        self.er_pick = ((self.challenger_pick.value) % 3)
        self.ee_pick = ((self.challengee_pick.value) %3)
        
        if self.er_pick == self.ee_pick:
            await ctx.edit_response('It was a tie!')
        # rock = 0, paper = 1, scissors = 2
        elif ((
            self.er_pick == 1 and self.ee_pick == 0
          ) or (
            self.er_pick == 0 and self.ee_pick == 2
          ) or (
            self.er_pick == 2 and self.ee_pick == 1
        )):
            await ctx.edit_response(
              f'{self.message_emojis[self.er_pick]} '
              f'>>> {self.message_emojis[self.ee_pick]}\n'
              f'{self.challenger_pick.name} beats '
              f'{self.challengee_pick.name.lower()}, '
              f'{self.challenger.mention} wins!'
            )
        else:
            await ctx.edit_response(
              f'{self.message_emojis[self.ee_pick]} '
              f'>>> {self.message_emojis[self.er_pick]}\n'
              f'{self.challengee_pick.name} beats '
              f'{self.challenger_pick.name.lower()}, '
              f'{self.challengee.mention} wins!'
            )
        self.stop()

    @miru.button(label='Rock', emoji='\N{ROCK}',
                 style=hikari.ButtonStyle.PRIMARY)
    async def rock_button(self, ctx: miru.ViewContext,
                          button: miru.Button) -> None:
        """Handle the rock button being clicked."""
        if ctx.user.username == self.challenger.username:
            self.challenger_pick = RPSPick.Rock
        else:
            self.challengee_pick = RPSPick.Rock
        await self.determine_winner(ctx)

    @miru.button(label='Paper', emoji='\N{SCROLL}',
                 style=hikari.ButtonStyle.PRIMARY)
    async def paper_button(self, ctx: miru.ViewContext,
                           button: miru.Button) -> None:
        """Handle the paper button being clicked."""
        if ctx.user.username == self.challenger.username:
            self.challenger_pick = RPSPick.Paper
        else:
            self.challengee_pick = RPSPick.Paper
        await self.determine_winner(ctx)

    @miru.button(label='Scissors', emoji='\N{BLACK SCISSORS}',
                 style=hikari.ButtonStyle.PRIMARY)
    async def scissors_button(self, ctx: miru.ViewContext,
                              button: miru.Button) -> None:
        """Handle the scissors button being clicked."""
        if ctx.user.username == self.challenger.username:
            self.challenger_pick = RPSPick.Scissors
        else:
            self.challengee_pick = RPSPick.Scissors
        await self.determine_winner(ctx)

    async def view_check(self, ctx: miru.ViewContext) -> bool:
        """Before calling button methods check if presser is allowed user."""
        return (ctx.user.username == self.challenger.username or
                ctx.user.username == self.challengee.username)


@plugin.include
@docstrings.parse_doc
@crescent.command(name='rpschallenge', dm_enabled=False)
class RPSChallengeCommand:
    """
    Challenge a user to rock paper scissors.

    Requested by iluka wighton(razer304).
    Implemented by something sensible(somethingsensible) &
                   Camtas(camtas).

    Args:
        user: User to challenge.
    """

    user = crescent.option(hikari.User)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle rpschallenge command being run by showing button view."""
        view = RPSView()
        view.challenger = ctx.user
        view.challengee = self.user.user
        await ctx.respond(
          f'{self.user.user.mention} '
          'You have been challenged to Rock Paper Scissors!\n'
          'Both players now need to make their decision below:',
          components=view
        )
        plugin.model.miru.start_view(view)
