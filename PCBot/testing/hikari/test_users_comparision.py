# Copyright (c) 2020 Tomxey
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import datetime
from hikari import interactions, permissions, snowflakes, users


def make_user(app, user_id, username):
    return users.UserImpl(
          app=app,
          id=snowflakes.Snowflake(user_id),
          discriminator="0001",
          username=username,
          global_name=None,
          avatar_hash=None,
          banner_hash=None,
          accent_color=None,
          is_bot=False,
          is_system=False,
          flags=users.UserFlag.NONE,
      )


# Based on make_guild_member
def make_interactions_member(app, user_id, username):
    user = make_user(app, user_id, username)
    return interactions.base_interactions.InteractionMember(
        user=user,
        guild_id=snowflakes.Snowflake(2233),
        role_ids=[],
        joined_at=datetime.datetime.now(),
        nickname=user.username,
        premium_since=None,
        guild_avatar_hash="no",
        is_deaf=False,
        is_mute=False,
        is_pending=False,
        raw_communication_disabled_until=None,
        permissions=permissions.Permissions.NONE
    )
