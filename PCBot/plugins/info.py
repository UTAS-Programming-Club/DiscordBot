"""This module contains the bot's plugin info command."""

import crescent
import hikari
import json
import requests
import time
from crescent.ext import docstrings
from jwt import JWT, jwk_from_pem
from pathlib import Path
from PCBot.botdata import gh_pem_path

plugin = crescent.Plugin[hikari.GatewayBot, None]()

github_app_client_id = '865339'
github_app_installation_id = '49024845'
github_api_url = 'https://api.github.com/'
github_api_headers = {
  'Accept': 'application/vnd.github+json',
  'User-Agent': 'UTAS-Programming-Club',
  'X-GitHub-Api-Version': '2022-11-28'
}

# TODO: Decide on commit['author']['date'] and commit['committer']['date']
#       Can be different if cherrypicking, merging, rebasing, ...
# TODO: Show committer as well
# TODO: Add a general url to any(perhaps dict and list enough?) function
# TODO: Allow changing account and repo


# From https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app#example-using-python-to-generate-a-jwt # noqa
def gh_generate_jwt() -> str:
    pem_path = Path(gh_pem_path)
    if not pem_path.is_file():
        raise Exception('Required private pem secret is missing')
    with open(pem_path, 'rb') as pem_file:
        pem = pem_file.read()
        signing_key = jwk_from_pem(pem)
    current_time = int(time.time())
    jwt_payload = {
        # Allow for clock drift by issuing 1 minute in the past
        'iat': current_time - 60,
        # Allow use for up to 1 minute
        'exp': current_time + 60,
        'iss': github_app_client_id
    }
    jwt_inst = JWT()
    return jwt_inst.encode(jwt_payload, signing_key, alg='RS256')


def gh_start_app_session(jwt: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(github_api_headers)
    s.headers['Authorization'] = f'Bearer {jwt}'
    r = s.get(github_api_url + 'app/installations')
    if not r.ok:
        raise Exception('Unable to authenticate app with github')
    return s


def gh_start_installation_session(s: requests.Session) -> None:
    r = s.post((github_api_url
                + f'app/installations/{github_app_installation_id}/'
                  'access_tokens'))
    if not r.ok:
        raise Exception('Unable to authenticate installation with github')
    token_info = json.loads(r.content)
    s.headers['Authorization'] = f"Bearer {token_info['token']}"
    r = s.get(github_api_url + 'meta')
    if not r.ok:
        raise Exception('Unable to authenticate installation with github')


def gh_get_branches(s: requests.Session) -> list:
    r = s.get((github_api_url
               + 'repos/UTAS-Programming-Club/DiscordBot/branches'))
    if not r.ok:
        raise Exception('Unable to access repo branches')
    return json.loads(r.content)


def gh_get_branch(s: requests.Session, name) -> dict:
    r = s.get((github_api_url
               + 'repos/UTAS-Programming-Club/DiscordBot/branches/' + name))
    if not r.ok:
        raise Exception('Unable to access repo branch')
    return json.loads(r.content)


def gh_get_commit(s: requests.Session, url: str) -> dict:
    r = s.get(url)
    if not r.ok:
        raise Exception('Unable to access repo commit')
    return json.loads(r.content)


def gh_get_forks(s: requests.Session) -> list:
    r = s.get(github_api_url + 'repos/UTAS-Programming-Club/DiscordBot/forks')
    if not r.ok:
        raise Exception('Unable to access repo forks')
    return json.loads(r.content)


def gh_get_fork_events(s: requests.Session, url: str) -> dict:
    r = s.get(url)
    if not r.ok:
        raise Exception('Unable to access repo fork events')
    return json.loads(r.content)



@plugin.include
@docstrings.parse_doc
@crescent.command(name='info')
class InfoCommand:
    """
    Provide infomation about about the bot.

    Requested by something sensible(somethingsensible).
    Implemented by something sensible(somethingsensible).
    """

    public = crescent.option(bool, 'Show response publicly', default=False)

    async def callback(self, ctx: crescent.Context) -> None:
        """Handle info command being run."""
        await ctx.defer(ephemeral=not self.public)
        output = ''
        jwt = gh_generate_jwt()
        s = gh_start_app_session(jwt)
        gh_start_installation_session(s)
        branches = gh_get_branches(s)
        output += 'DiscordBot branches:'
        for branch in branches:
            branch_info = gh_get_branch(s, branch['name'])
            commit_info = gh_get_commit(s, branch['commit']['url'])
            output += (f"\n[{branch['name']}]"
                       f"(<{branch_info['_links']['html']}>)\n")
            output += (f"\t[{commit_info['commit']['author']['name']}]"
                       f"(<{commit_info['author']['html_url']}>)"
                       f" [{commit_info['commit']['author']['date']}]"
                       f"(<{commit_info['html_url']}>)\n")
            full_message = commit_info['commit']['message']
            output += '\t' + full_message.split('\n')[0] + '\n'
        output += '\nDiscordBut forks:'
        forks = gh_get_forks(s)
        for fork in forks:
            events = gh_get_fork_events(s, fork['events_url'])
            output += (f"\n[{fork['name']}](<{fork['html_url']}>) by"
                       f" [{fork['owner']['login']}]"
                       f"(<{fork['owner']['html_url']}>)\n")
            last_push = next((event for event in events 
                              if event['type'] == 'PushEvent'),
                             None)
            if last_push is None or len(last_push['payload']['commits']) == 0:
                continue
            output += '    Most recent commit:\n'
            last_commit_url = last_push['payload']['commits'][-1]['url']
            last_commit_info = gh_get_commit(s, last_commit_url)
            output += (f"\t\t[{last_commit_info['commit']['author']['name']}]"
                       f"(<{last_commit_info['author']['html_url']}>)"
                       f" [{last_commit_info['commit']['author']['date']}]"
                       f"(<{last_commit_info['html_url']}>)\n")
            full_message = last_commit_info['commit']['message']
            output += '\t\t' + full_message.split('\n')[0] + '\n'
        
        await ctx.respond(output)
