"""This module contains functions used to handle replies to bot messages."""

from crescent import event, Plugin
from collections.abc import Awaitable, Callable
from hikari import GatewayBot, MessageCreateEvent
from typing import Optional

plugin = Plugin[GatewayBot, None]()

# Cannot assign value here because the assignment
# happens every time this module is imported
reply_handlers: Optional[
  list[Callable[[MessageCreateEvent], Awaitable[None]]]
]


def reset_reply_handler():
    """Reset list of reply handlers on bot start and reload."""
    global reply_handlers
    reply_handlers = []


def add_reply_handler(
  func: Callable[[MessageCreateEvent], Awaitable[None]]
):
    """Add reply handler to be called when a reply is received."""
    if 'reply_handlers' not in globals():
        reset_reply_handler()
    reply_handlers.append(func)


@plugin.include
@event
async def on_message_create(event: MessageCreateEvent):
    """Pass messages to each registered reply handler."""
    if 'reply_handlers' not in globals():
        return
    for reply_handler in reply_handlers:
        await reply_handler(event)
