import crescent
import hikari

# Load bot token
with open("./secrets/token") as f:
  token = f.read().strip()

bot = hikari.GatewayBot(token, intents=hikari.Intents.GUILD_MESSAGES)
client = crescent.Client(bot)

# Load plugins
client.plugins.load_folder("PCBot.plugins")

# Run the bot.
if __name__ == "__main__":
  bot.run()
