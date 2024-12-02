"""This module contains the bot's dectalk tts command."""

# TODO: Check that the bot is allowed to join the provided channel

import asyncio
import crescent
import hikari
import os
import socket
import subprocess
import sys
from crescent.ext import docstrings
from PCBot.botdata import (
    BotData, lavalink_password_path, get_token_file_path,
    ongaku_available
)
if not ongaku_available:
    raise Exception('dectalk uses hikari-ongaku which is not available')
import ongaku
from ongaku.ext import checker

if not os.path.isfile('dectalk/Lavalink.jar') or \
   not os.path.isfile('dectalk/dectalk/say'):
    raise Exception('Unable to find required dectalk files')

plugin = crescent.Plugin[hikari.GatewayBot, BotData]()
lavalink_port = 2333
first_call = True

with open(get_token_file_path(lavalink_password_path)) as f:
    lavalink_password = f.read().strip()


def start_lavalink():
    """Start lavalink voice server."""
    environ = os.environ.copy()
    environ['SERVER_PORT'] = str(lavalink_port)
    environ['LAVALINK_SERVER_PASSWORD'] = lavalink_password
    subprocess.Popen(
        ['java', '-jar', './Lavalink.jar'],
        cwd='./dectalk',
        env=environ
    )


def run_dectalk(text: str, guild_id: hikari.Snowflake) -> str:
    name = f'{guild_id}.wav'
    subprocess.run(
        ['dectalk/dectalk/say', '-a', text, '-fo', f'dectalk/{name}']
    )
    return name


async def fetch_player(guild_id: hikari.Snowflake) -> ongaku.Player | None:
    """Return a functional ongaku player object."""
    # TODO: Figure out why player.connect fails with SessionStartException
    #       on the first attempt since starting the bot
    try:
        session = await plugin.model.ongaku_client.session.fetch('dectalk')
    except ValueError:
        session = await plugin.model.ongaku_client.session.create('dectalk')

    try:
        return await session.player.fetch_player(guild_id)
    except ongaku.PlayerMissingException:
        return await session.player.create_player(guild_id)

    # TODO: Figure out why player.play fails with PlayerException if lavalink
    #       is not running when the bot starts with this code
    # try:
    #     return await plugin.model.ongaku_client.player.fetch(guild_id)
    # except ongaku.PlayerMissingException:
    #     return await plugin.model.ongaku_client.player.create(guild_id)

    return None


@plugin.include
@crescent.event
async def track_end_event(event: ongaku.TrackEndEvent):
    """Disconnect the bot from vc after the audio finishes playing."""
    try:
        player = await fetch_player(event.guild_id)
        await player.disconnect()
    finally:
        pass


@plugin.include
@docstrings.parse_doc
@crescent.command(name='dectalk')
class DecTalkCommand:
    """
    Read out provided text in voice chat using dectalk.

    Requested by Kat(kopy_kat).
    Implemented by something sensible(somethingsensible).
    """

    text = crescent.option(str, 'Text to speak')
    channel = crescent.option(
        hikari.GuildVoiceChannel, 'Channel to speak in', default=None
    )

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle dectalk command being run."""
        sent_message = False

        wav_name = run_dectalk(self.text, ctx.guild_id)

        if self.channel is None:
            voice_state = ctx.client.app.cache.get_voice_state(
                ctx.guild_id, ctx.user.id
            )
            if not voice_state or not voice_state.channel_id:
                await ctx.respond(
                    'Either provide a channel name or join a channel',
                    ephemeral=True
                )
                return
            channel_id = voice_state.channel_id
        else:
            channel_id = self.channel.id

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', lavalink_port)) != 0:
                await ctx.respond('Starting lavalink', ephemeral=True)
                sent_message = True
                start_lavalink()
                await asyncio.sleep(10)
                if s.connect_ex(('localhost', lavalink_port)) != 0:
                    await ctx.edit('Failed to start lavalink')
                    return

        player = await fetch_player(ctx.guild_id)

        global first_call
        if not player.connected:
            try:
                await player.connect(channel_id, deaf=True)
            except ongaku.SessionStartException:
                if first_call:
                    first_call = False
                    if sent_message:
                        await ctx.edit(
                            'Setup complete, run command again to use dectalk'
                        )
                    else:
                        await ctx.respond(
                            'Setup complete, run command again to use dectalk',
                            ephemeral=True
                        )
                else:
                    if sent_message:
                        await ctx.edit('Failed to join voice channel')
                    else:
                        await ctx.respond(
                            'Failed to join voice channel', ephemeral=True
                        )
                return

        if sent_message:
            await ctx.delete()
        first_call = False

        # TODO: Check if this is needed?
        checked_query = await checker.check(wav_name)
        if checked_query.type != checker.CheckedType.QUERY:
            await ctx.respond(
              'Failed to look for dectalk matches', ephemeral=True
            )
            return

        track = await ctx.client.model.ongaku_client.rest.track.load(
            checked_query.value
        )
        if track is None:
            await ctx.respond('No dectalk matches were found', ephemeral=True)
            return

        if not isinstance(track, ongaku.Track):
            await ctx.respond('Unable to select dectalk track', ephemeral=True)
            return

        await ctx.respond(f'Playing {track.info.uri}')
        await player.play(track)
