from typing import List, Dict
from dataclasses import dataclass

import sentry_sdk
from discord.ext import commands


@dataclass
class Delta:
    removed: List[str]
    used: Dict[str, int]


def use_sentry(client, **sentry_args):
    """
    Use this compatibility library as a bridge between Discord and Sentry.
    Arguments:
        client: The Discord client object (e.g. `discord.AutoShardedClient`).
        sentry_args: Keyword arguments to pass to the Sentry SDK.
    """

    sentry_sdk.init(**sentry_args)

    @client.event
    async def on_error(event, *args, **kwargs):
        """Don't ignore the error, causing Sentry to capture it."""
        raise

    @client.event
    async def on_command_error(msg, error):
        # don't report errors to sentry related to wrong permissions
        if not isinstance(error, (commands.MissingRole, commands.MissingAnyRole)):
            raise error


def find_delta(before: Dict[str, int], after: Dict[str, int]) -> Delta:
    removed = []
    used = {}

    for url, _ in before.items():
        if url not in after:
            removed.append(url)

    for url, uses in after.items():
        if url in before:
            delta_uses = uses - before.get(url, 0)
            if delta_uses != 0:
                used[url] = delta_uses
        elif uses != 0:
            used[url] = uses

    return Delta(removed=removed, used=used)
