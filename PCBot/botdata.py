"""This module contains the plugin shared data class."""

import dataclasses
import miru

@dataclasses.dataclass
class BotData:
    """Store data used in plugins, passed to crescent at startup as a model."""

    miru: miru.Client

