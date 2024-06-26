"""This module contains the plugin shared data class."""

import dataclasses
import miru
import os
import sys

if sys.version_info.minor >= 11:
    import ongaku


@dataclasses.dataclass
class BotData:
    """Store data used in plugins, passed to crescent at startup as a model."""

    miru: miru.Client
    if sys.version_info.minor >= 11:
      ongaku_client: ongaku.Client


token_path = './secrets/token'
lavalink_password_path = './secrets/lavalink'
guild_id_path = './secrets/guild'
gh_pem_path = './secrets/gh_private.pem'


def get_token_file_path(file: str) -> str:
    """Append .txt to file path if that file exists.

       Makes it easier to setup the bot on windows.
    """
    if os.path.isfile(file + '.txt'):
        return file + '.txt'
    return file
