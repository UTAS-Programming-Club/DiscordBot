# Install Packages
```sh
pip install -r requirements3.10.txt # For python 3.10
pip install -r requirements3.11.txt # For python 3.11, required for dectalk plugin
```

# Setup
Place a discord bot token from discord's [developer portal](https://discord.com/developers/applications) in secrets/token(.txt)
Place a discord guild id in secrets/guild(.txt)
Place a github private pem in secrets/gh_private.pem, currently this has to be one for the programming club's github app but that can change

# Testing Bot
```sh
python -m PCBot
```

# Deploying Bot
```sh
python -O -m PCBot
```
This should be -OO but currently that causes a error inside crescent.

# Desired Features
PC club members are welcome to contribute and there is a section in each docstring for credits
* Option to avoid "An unexpected error occurred." after every issue, only useful if locally running the script
* Type checking
* PEP8 AND PEP257 checking, https://www.codewof.co.nz/style/python3/ works until that happens though
* Combine previous with formatter, yapf, black?
* Show full command docstrings somewhere, help command? Then have non pinging mentions for required and implemented by lines
* Log all run commands with the requester's name in the console
* Make sure all command docstrings have requested by, implemented by and arguments sections for help command
* More commands
* Support for more python versions than just 3.10 and 3.11
* Make guild id optional
* Add options to start into mocking mode for each command
* Auto reload of a command on run/file change
* Anything listed as TODO within the plugins


Based on https://github.com/hypergonial/hikari-intro/