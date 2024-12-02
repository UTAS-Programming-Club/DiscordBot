"""This module contains the bot's plugin reloading command."""

import crescent
import hikari
from json import load
from operator import itemgetter
from PCBot.botdata import BotData
from tabulate import tabulate

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()


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
        with open("./data/aoc-leaderboard.json") as file:
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
            player["stars"],
            f"`{user_mapping[player["name"]].mention}`"
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
          "Username", "Star count", "Discord".ljust(max_display_len + 1, " ")
        ], tablefmt="heavy_outline")
        table_lines = table.split("\n")

        for i in range(3):
            output += f"`{table_lines[i][1:-1]}`\n"

        for i, player in enumerate(data):
            output += "`"
            aoc_name = player[0]
            if aoc_name not in user_mapping:
                output += table_lines[i + 3][1:-1].rsplit("┃", 1)[0] + "┃`"
            else:
                output += table_lines[i + 3][1:-1].rsplit("`", 2)[0][:-2]
                output += "┃` " + user_mapping[aoc_name].mention
            output += "\n"

        output += f"`{table_lines[-1][1:-1]}`"

        await ctx.respond(output, user_mentions=False)
