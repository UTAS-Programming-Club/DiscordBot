# Install Packages
```sh
pip install -r requirements.txt
```

# Setup
Place a discord bot token in secrets/token

# Testing Bot
```sh
python -m PCBot
```

# Deploying Bot
```sh
python -OO -m PCBot
```

# Desired Features
PC club members are welcome to contribute and there is a section in each docstring for credits
* Type checking
* PEP8 AND PEP257 checking, https://www.codewof.co.nz/style/python3/ works until that happens though
* Show full command docstrings somewhere, help command? Then have non pinging mentions for required and implemented by lines
* Make guild id accessable to all plugins, I don't think BotData cannot be used since the plugin is unloaded when it is needed
* More commands
* Anything listed as TODO within the plugins


Based on https://github.com/hypergonial/hikari-intro/