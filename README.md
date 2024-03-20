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
* Option to avoid "An unexpected error occurred." after every issue, only useful if locally running the script
* Type checking
* PEP8 AND PEP257 checking, https://www.codewof.co.nz/style/python3/ works until that happens though
* Combine previous with formatter, yapf, black?
* Show full command docstrings somewhere, help command? Then have non pinging mentions for required and implemented by lines
* Log all run commands with the requester's name in the console
* More commands
* Anything listed as TODO within the plugins


Based on https://github.com/hypergonial/hikari-intro/