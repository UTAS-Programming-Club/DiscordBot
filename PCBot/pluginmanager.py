import crescent
from collections import Counter

def get_plugin_names(plugins: crescent.PluginManager) -> Counter[str]:
        return Counter(plugins.plugins.keys())
