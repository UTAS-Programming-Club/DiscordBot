"""This module contains the plugin shared data class."""

import crescent
import dataclasses
import miru
import sys
from collections import Counter

# TODO: Replace modules/getattr with typing.reveal_type usage in plugins


@dataclasses.dataclass
class BotData:
    """Store data used in plugins, passed to crescent at startup as a model."""

    miru: miru.Client
    plugin_names: Counter[str]

    def update_plugins(self, loaded_plugins: list[crescent.Plugin]) -> None:
        """Update plugin_names given a list of crescent's loaded plugins."""
        new_plugins: list[str] = []
        for module_name, module in sys.modules.items():
            if 'PCBot.plugins.' not in module_name:
                continue
            new_plugin = getattr(module, 'plugin', None)
            if new_plugin not in loaded_plugins:
                continue
            module_file_name = module_name.split('.')[-1]
            new_plugins.append(module_file_name)
        # Counter only guarantees that order will be retained on python >= 3.7
        self.plugin_names = Counter(sorted(new_plugins))
