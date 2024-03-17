import crescent
import hikari
import miru
from crescent.ext import docstrings
from enum import Enum
from PCBot.botdata import botdata
from typing import Optional

# Load guild id
with open('./secrets/guild') as f:
  guildId = int(f.read().strip())

plugin = crescent.Plugin[hikari.GatewayBot, botdata]()

# Not useful for this as command options can be seen by users.
# Keeping as autocomplete may be useful for something else.
#async def rps_autocomplete_response(
#  ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
#) -> list[tuple[str, str]]:
#  return
#
#async def fetch_rps_autocomplete_options(
#  ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
#) -> list[tuple[str, str]]:
#    _options = await ctx.fetch_options()
#    return []

# Not useful returning False modal_check still closes the Modal.
# I was hoping that it would show an error and allow changing input.
# Keeping as it may be useful for something else.
#class RPSModal(miru.Modal, title = 'Rock Paper Scissors'):
#  pick = miru.TextInput(
#    label = 'Rock, Paper or Scissors',
#    required = True,
#    min_length = 4,
#    max_length = 8,
#  )
#
#  async def modal_check(self, ctx: miru.ModalContext) -> bool:
#    if ctx.values[self.pick].casefold() in ['rock', 'paper', 'scissors']:
#      return True
#    else:
#      await ctx.respond(f'You entered "{ctx.values[self.pick]}" which is not allowed')
#      return False
#
#  # The callback function is called after the user hits 'Submit'
#  async def callback(self, ctx: miru.ModalContext) -> None:
#    # You can also access the values using ctx.values,
#    # Modal.values, or use ctx.get_value_by_id()
#    await ctx.respond(
#      f'You picked {self.pick.value}'
#    )
#
# Above is sent with:
# modal = RPSModal()
# builder = modal.build_response(ctx.client.model.miru)
# await ctx.respond_with_builder(builder)
# ctx.client.model.miru.start_modal(modal)

class RPSPick(Enum):
  Rock     = 1
  Paper    = 2
  Scissors = 3

# TODO: Prevent users changing their pick
# TODO: Tell user when their pick has been received
# TODO: Report timeout
# TODO: Disable buttons visibly after the round is over or timeout has occurred

class RPSView(miru.View):
  challenger: hikari.User
  challengee: hikari.User
  challengerPick: Optional[RPSPick] = None
  challengeePick: Optional[RPSPick] = None

  async def determine_winner(self, ctx: miru.ViewContext) -> None:
    if self.challengerPick is None or self.challengeePick is None:
      return
    if self.challengerPick == self.challengeePick:
      await ctx.edit_response(f'It was a tie!')
    elif ((self.challengerPick is RPSPick.Paper and self.challengeePick is RPSPick.Rock) or
       (self.challengerPick is RPSPick.Scissors and self.challengeePick is RPSPick.Paper) or
       (self.challengerPick is RPSPick.Rock and self.challengeePick is RPSPick.Scissors)):
      await ctx.edit_response(f'{self.challengerPick.name} beats {self.challengeePick.name.lower()}, {self.challenger.mention} wins!')
    else:
      await ctx.edit_response(f'{self.challengeePick.name} beats {self.challengerPick.name.lower()}, {self.challengee.mention} wins!')
    self.stop()

  @miru.button(label='Rock', emoji='\N{ROCK}', style=hikari.ButtonStyle.PRIMARY)
  async def rock_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
    if ctx.user.username == self.challenger.username:
      self.challengerPick = RPSPick.Rock
    else:
      self.challengeePick = RPSPick.Rock
    await self.determine_winner(ctx)

  @miru.button(label='Paper', emoji='\N{SCROLL}', style=hikari.ButtonStyle.PRIMARY)
  async def paper_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
    if ctx.user.username == self.challenger.username:
      self.challengerPick = RPSPick.Paper
    else:
      self.challengeePick = RPSPick.Paper
    await self.determine_winner(ctx)

  @miru.button(label='Scissors', emoji='\N{BLACK SCISSORS}', style=hikari.ButtonStyle.PRIMARY)
  async def scissors_button(self, ctx: miru.ViewContext,  button: miru.Button) -> None:
    if ctx.user.username == self.challenger.username:
      self.challengerPick = RPSPick.Scissors
    else:
      self.challengeePick = RPSPick.Scissors
    await self.determine_winner(ctx)

  async def view_check(self, ctx: miru.ViewContext) -> bool:
    #await ctx.respond(f'{ctx.user.username} pressed a button')
    #await ctx.respond(
    #  f'Challenger: {self.challenger.username}\n'
    #  f'Challengee: {self.challengee.username}\n'
    #  f'BtnPresser: {ctx.user.username}'
    #)
    return ctx.user.username == self.challenger.username or ctx.user.username == self.challengee.username

@plugin.include
@docstrings.parse_doc
@crescent.command(guild = guildId, dm_enabled = False)
class rpschallenge:
  """
  Challenge a user to rock paper scissors.
  
  Requested by iluka wighton(razer304).
  Implemented by something sensible(somethingsensible).
  
  Args:
      user: User to challenge.
  """
  #pick: Your pick, this is not shown to the other user.
  user = crescent.option(hikari.User)
  
  async def callback(self, ctx: crescent.Context) -> None:
    view = RPSView()
    view.challenger = ctx.user
    view.challengee = self.user.user
    await ctx.respond(
      f'{self.user.user.mention} You have been challenged to Rock Paper Scissors!\n'
       'Both players now need to make their decision below:',
      components = view
    )
    ctx.client.model.miru.start_view(view)
