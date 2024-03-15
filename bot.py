import discord
from discord.ext import commands

# For Programming Club server and bot
discordBotToken = 'PUT TOKEN HERE'

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    channel = bot.get_channel(int(1218088677700534272))
    #print(channel)
    #print(type(bot))
    #await channel.send('on_ready')

@bot.command()
async def rpschallenge(ctx, username: discord.Member, request):
    await ctx.send(f'test')
    
@bot.hybrid_command()
async def restart(ctx, arg):
    print(type(ctx))
    await bot.close()
    await bot.login(discordBotToken)

#try:
bot.run(discordBotToken)
#except:
#    print('Error: Bot crashed')
#    exit(1)
