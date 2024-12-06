"""This module contains the bot's plugin aoc leaderboard command."""

import crescent
from crescent.ext import tasks
from datetime import datetime, timedelta
from enum import Enum
from hikari import AutocompleteInteractionOption, GatewayBot
from hikari.embeds import Embed, EmbedField
from json import load
from logging import getLogger
from operator import itemgetter
from os import path
from PCBot.botdata import (
  aoc_cookie_path, BotData, get_token_file_path, guild_id_path
)
from requests import get
from tabulate import tabulate
from time import time
from zoneinfo import ZoneInfo

leaderboard_path = "./data/aoc-leaderboard.json"
leaderboard_refresh_interval = 1800  # 30 minutes
logger = getLogger(__name__)
plugin = crescent.Plugin[GatewayBot, BotData]()

# Load aoc cookie
with open(get_token_file_path(aoc_cookie_path)) as file:
    session_cookie = file.read().strip()

# Load guild id
with open(get_token_file_path(guild_id_path)) as f:
    guild_id = int(f.read().strip())


async def fetch_leaderboard() -> None:
    """Check if leaderboard is stale and update if needed."""
    last_modify_time = path.getmtime(leaderboard_path)
    diff = time() - last_modify_time

    if diff >= leaderboard_refresh_interval:
        logger.info("Updating leaderboard")

        leaderboard_url = \
          "https://adventofcode.com/2024/leaderboard/private/view/2494838.json"
        headers = {'Cookie': session_cookie}
        request = get(leaderboard_url, headers=headers)

        if request.status_code != 200:
            return

        with open(leaderboard_path, "w") as file:
            file.write(request.text)

async def update_names() -> None:
    with open("./data/aoc-usermapping.json") as file:
        mapping = load(file)

    user_mapping = {
        user["aoc"]: [
            await plugin.app.rest.fetch_member(
              guild_id, user=user["discord"]
            )
        ]
        for user in mapping
        if "update_name" in user and user["update_name"]
    }

    with open(leaderboard_path) as file:
        leaderboard = load(file)

    user_data = [
      [
        player["stars"],
        user_mapping[player["name"]][0]
      ]
      for player in leaderboard["members"].values()
      if player['stars'] != 0 and player["name"] in user_mapping
    ]

    for user in user_data:
        name = user[1].nickname.rsplit("[")[0]
        await user[1].edit(nickname=f"{name}[📅🎄{user[0]}⭐]")


def get_remaining_time() -> timedelta:
    timezone = ZoneInfo("Etc/GMT+5")
    now = datetime.now(timezone)
    last_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight = last_midnight + timedelta(days=1)

    return next_midnight - now


class ScoreType(Enum):
    Score = 0
    Stars = 1
    Both  = 2

async def autocomplete_score_type(
  ctx: crescent.AutocompleteContext, option: AutocompleteInteractionOption
) -> list[tuple[str, str]]:
    # I tried (st.name, st) but that gives "Object of type ScoreType is not JSON serializable"
    return [(st.name, st.name) for st in ScoreType]


@plugin.include
@tasks.loop(hours=0, minutes=30, seconds=0)
async def update_leaderboard() -> None:
    await fetch_leaderboard()
    await update_names()

@plugin.include
@crescent.command(name="aoc", description="Fetch 2024 AOC leaderboard.")
class AOCCommand:
    """
    Display cached 2024 AOC leaderboard.

    Requested by Ian Lewis(giant_ian) & Lindsay Wells(giantlindsay).
    Implemented by something sensible(somethingsensible).
    """

    score_type = crescent.option(
      str, "Which score type(s) to display, only for new format",
      autocomplete=autocomplete_score_type, default=ScoreType.Both.name
    )

    use_old_format = crescent.option(
      bool, "Use custom column format", default=False
    )

    async def get_mapping(self, ctx: crescent.Context) -> (list, int):
        """Create table with optional info about aoc participants."""
        with open("./data/aoc-usermapping.json") as file:
            mapping = load(file)

        user_mapping = {}
        max_display_len = 0

        for user in mapping:
            member = await ctx.app.rest.fetch_member(
             ctx.guild_id, user=user["discord"]
            )
            user_mapping[user["aoc"]] = [
              user["language"] if "language" in user else "",
              member,
              user["update_name"] if "update_name" in user else False
            ]
            max_display_len = max(max_display_len, len(member.display_name))

        return (user_mapping, max_display_len)

    def get_users(self, user_mapping: list, score_type: ScoreType)\
      -> (list, int):
        """Create table with displayed info about aoc participants."""
        with open(leaderboard_path) as file:
            leaderboard = load(file)

        user_data = [
          [
            player["name"],
            player["local_score"],
            player["stars"],
            user_mapping[player["name"]][0]
              if player["name"] in user_mapping
              else "",
            user_mapping[player["name"]][1].mention
              if player["name"] in user_mapping
              else ""
          ]
          for player in leaderboard["members"].values()
          if player['stars'] != 0
        ]

        # Sort by name, alphabetically
        user_data.sort(key=itemgetter(0))

        # TODO: Support sorting via stars even with score shown
        # Sort via score or stars, highest at the top
        if score_type in [ScoreType.Score, ScoreType.Both]:
            user_data.sort(key=itemgetter(1), reverse=True)
        elif score_type in [ScoreType.Stars]:
            user_data.sort(key=itemgetter(2), reverse=True)

        return (user_data, leaderboard["event"])

    def create_custom_table(self, user_data: list, max_display_len: int)\
      -> str:
        """Create string containing table with info about aoc participants."""

        for data in user_data:
            data[2] =  f"{data[2]} ⭐  *"

        table_data = tabulate(user_data, headers=[
          "Username", "Score", "Star count", "Language(s)",
          "Discord".ljust(max_display_len + 1, " ")
        ], colalign=("left", "right", "right"),
          tablefmt="heavy_outline")
        table_lines = table_data.split("\n")

        table_output = ""

        for i in range(3):
            table_output += f"`{table_lines[i][1:-1]}`\n"

        for i, player in enumerate(user_data):
            table_output += "`"
            components = table_lines[i + 3][1:-1].rsplit("┃", 3)
            table_output += components[0] + "┃"\
                         +  "  " + components[1][:-2] + "┃"\
                         +  components[2] + "┃"\
                         +  "`" + components[3] + "\n"

        table_output += f"`{table_lines[-1][1:-1]}`"

        return table_output

    def create_embed_table(self, user_data: list, score_type: ScoreType)\
      -> Embed:
        embed = Embed()

        usernames = ""
        scores = ""
        languages = ""

        max_score_len = max(len(str(user[1])) for user in user_data)
        max_stars_len = max(len(str(user[2])) for user in user_data)

        for user in user_data:
            username = user[4] if user[4] != "" else user[0]
            score = str(user[1]).rjust(max_score_len, " ")
            stars = str(user[2]).rjust(max_stars_len, " ")
            # Discord removes lines containing only a new line or common blank chars
            language = user[3] if user[3] != "" else "᠎"

            usernames += username + "\n"

            scores += "`"
            match score_type:
                case ScoreType.Score:
                    scores += score + "`"
                case ScoreType.Stars:
                    scores += stars + "` ⭐"
                case ScoreType.Both:
                    scores += f"{score}, {stars}` ⭐"
            scores += "\n"

            languages += language + "\n"

        embed.add_field("Username", usernames, inline=True)
        embed.add_field("Score", scores, inline=True)
        embed.add_field("Language", languages, inline=True)

        return embed

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle aoc command being run by showing the leaderboard."""
        await fetch_leaderboard()

        score_type = ScoreType[self.score_type]

        (user_mapping, max_display_len) = await self.get_mapping(ctx)
        (user_data, year) = self.get_users(user_mapping, score_type)
        if self.use_old_format:
            table_output = self.create_custom_table(user_data, max_display_len)
            embed = None
        else:
            table_output = ""
            embed = self.create_embed_table(user_data, score_type)

        remaining_time = get_remaining_time()
        formatted_time = str(remaining_time).split(".")[0]

        output = f"Year: {year}\n"\
               + f"Time to next puzzle: {formatted_time}\n"\
               + table_output

        await ctx.respond(output, embed=embed, user_mentions=False)

        await update_names()
