import crescent
import hikari
import miru
from PCBot.botdata import botdata

# Load bot token
with open('./secrets/token') as f:
  token = f.read().strip()

# Create bot
bot = hikari.GatewayBot(token, intents=hikari.Intents.NONE)
miru_client = miru.Client(bot)
crescent_client = crescent.Client(bot, botdata(miru_client))

# Load plugins
crescent_client.plugins.load_folder('PCBot.plugins')

# Run the bot
if __name__ == '__main__':
  bot.run()
