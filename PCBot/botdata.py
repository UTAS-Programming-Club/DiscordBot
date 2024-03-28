"""This module contains the plugin shared data class."""

import dataclasses
import miru
import os


@dataclasses.dataclass
class BotData:
    """Store data used in plugins, passed to crescent at startup as a model."""

    miru: miru.Client


token_path = './secrets/token'
guild_id_path = './secrets/guild'


def get_token_file_path(file: str) -> str:
    """Append .txt to file path if that file exists.

       Makes it easier to setup the bot on windows.
    """
    if os.path.isfile(file + '.txt'):
        return file + '.txt'
    return file
