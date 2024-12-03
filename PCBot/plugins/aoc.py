"""This module contains the bot's plugin aoc leaderboard command."""

import crescent
from hikari import GatewayBot
from json import load
from logging import getLogger
from operator import itemgetter
from os import path
from PCBot.botdata import aoc_cookie_path, BotData, get_token_file_path
from requests import get
from tabulate import tabulate
from time import time

leaderboard_path = "./data/aoc-leaderboard.json"
leaderboard_refresh_interval = 1800  # 30 minutes
logger = getLogger(__name__)
plugin = crescent.Plugin[GatewayBot, BotData]()

# Load aoc cookie
with open(get_token_file_path(aoc_cookie_path)) as file:
    session_cookie = file.read().strip()


# TODO: Switch to crescent task
async def fetch_leaderboard(ctx: crescent.Context) -> bool:
    """Check if leaderboard is stale and update if needed."""
    last_modify_time = path.getmtime(leaderboard_path)
    diff = time() - last_modify_time

    if diff >= leaderboard_refresh_interval:
        logger.info("Updating leaderboard")

        await ctx.defer()

        leaderboard_url = \
          "https://adventofcode.com/2024/leaderboard/private/view/2494838.json"
        headers = {'Cookie': session_cookie}
        request = get(leaderboard_url, headers=headers)

        if request.status_code != 200:
            return False

        with open(leaderboard_path, "w") as file:
            file.write(request.text)

    return True

@plugin.include
@crescent.command(name="aoc", description="Fetch 2024 AOC leaderboard.")
class AOCCommand:
    """
    Display cached 2024 AOC leaderboard.

    Requested by Lindsay Wells(giantlindsay).
    Implemented by something sensible(somethingsensible).
    """

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle aoc command being run by showing the leaderboard."""
        await fetch_leaderboard(ctx)

        with open(leaderboard_path) as file:
            leaderboard = load(file)

        with open("./data/aoc-usermapping.json") as file:
            mapping = load(file)

        user_mapping = {}
        max_display_len = 0

        for user in mapping:
            user_mapping[user["aoc"]] = await ctx.app.rest.fetch_member(
              ctx.guild_id, user=user["discord"]
            )
            max_display_len = max(
              max_display_len, len(user_mapping[user["aoc"]].display_name)
            )

        data = [
          [
            player["name"],
            player["local_score"],
            f"{player["stars"]} ⭐  *",
            user_mapping[player["name"]].mention
              if player["name"] in user_mapping
              else ""
          ]
          for player in leaderboard["members"].values()
          if player['stars'] != 0
        ]
        data.sort(key=itemgetter(0))
        data.sort(key=itemgetter(1), reverse=True)

        output = f"Year: {leaderboard['event']}\n"

        table = tabulate(data, headers=[
          "Username", "Score", "Star count",
          "Discord".ljust(max_display_len + 1, " ")
        ], colalign=("left", "right", "right"),
          tablefmt="heavy_outline")
        table_lines = table.split("\n")

        for i in range(3):
            output += f"`{table_lines[i][1:-1]}`\n"

        for i, player in enumerate(data):
            output += "`"
            components = table_lines[i + 3][1:-1].rsplit("┃", 2)
            output += components[0] + "┃"\
                   +  "  " + components[1][:-2] + "┃"\
                   +  "`" + components[2]
            output += "\n"

        output += f"`{table_lines[-1][1:-1]}`"

        await ctx.respond(output, user_mentions=False)
