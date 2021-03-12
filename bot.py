import asyncio
import logging
from typing import List

import aioredis
from discord.ext import commands
from discord import Member, Embed, Intents, Role, Invite
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

import config
from constants import SENTRY_ENV_NAME, ROLES_CAN_CONTROL_BOT, INV_TO_ROLES, ROLE_ID_SEPARATOR, GUILD_INDEX
from utils import use_sentry, find_delta


# initialize bot params
intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="$invites.", help_command=None, intents=intents)


# init sentry SDK
use_sentry(
    bot,
    dsn=config.SENTRY_API_KEY,
    environment=SENTRY_ENV_NAME,
    integrations=[AioHttpIntegration()],
)

# setup logger
logging.basicConfig(filename="eco-invites.log", level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")
bot.remove_command(help)


async def get_sorted_invites(ctx) -> List[Invite]:
    """Get sorted invites in descending order"""
    guild = bot.get_guild(ctx.guild.id)
    invites = await guild.invites()
    sorted_invites = sorted(invites, key=lambda x: x.uses, reverse=True)
    return sorted_invites


async def get_roles_for_url(invite_url: str) -> List[Role]:
    """Get roles for invite url"""
    roles_ids_str = await bot.redis_client.hget(INV_TO_ROLES, invite_url, encoding="utf-8")
    roles_ids = [int(_) for _ in roles_ids_str.split(ROLE_ID_SEPARATOR)]
    return [_ for _ in bot.guilds[GUILD_INDEX].roles if _.id in roles_ids]


def widget_builder(invites, display_all=False):
    description_all = "Statistics for all URLs"
    description_uses = "Statistics for URLs which were used at least once"
    description = description_all if display_all else description_uses
    widget = Embed(description=description, color=0x03D692, title="Invitations Stats")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    for i in invites:
        if i.uses == 0 and not display_all:
            continue
        widget.add_field(
            name=f"{i.code}", value=f"Created by: {i.inviter.mention}\nUsed: `{i.uses}`\nLink: {i.url}", inline=False
        )
    return widget


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("list")
async def get_all_invites_with_roles(ctx):
    invites_to_roles = await bot.redis_client.hgetall(INV_TO_ROLES, encoding="utf-8")
    widget = Embed(description="List all connected invite URLs and roles", color=0x03D692, title="Invite-Roles list")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    for k, v in invites_to_roles.items():
        widget.add_field(name=f"<{k}>", value=" ".join(f"<@&{_}>" for _ in v.split(ROLE_ID_SEPARATOR)), inline=False)
    # if there are no invites display help message
    if not len(invites_to_roles.items()):
        widget.add_field(
            name="There are no invite URLs connected to roles",
            value="Add one via `$invites.connect URL @mention-role1 @mention-role2`",
            inline=False,
        )
    await ctx.send(embed=widget)


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("connect")
async def connect_invite_to_role(ctx, url: str = None, *roles):
    invites = await get_sorted_invites(ctx)
    invites_urls = [_.url for _ in invites]
    # validate syntax
    if not url or not roles:
        return await ctx.send("Wrong syntax, `$invites.connect URL @mention-role1 @mention-role2`")
    # validate url
    if url not in invites_urls:
        return await ctx.send("Invite URL isn't valid")
    # parse roles
    roles_obj_list = []
    for role in roles:
        try:
            _role = await commands.RoleConverter().convert(ctx, role)
            roles_obj_list.append(str(_role.id))
        except (commands.CommandError, commands.BadArgument):
            return await ctx.send("Wrong syntax, `$invites.connect URL @mention-role1 @mention-role2`")
    await bot.redis_client.hset(INV_TO_ROLES, url, ROLE_ID_SEPARATOR.join(roles_obj_list))
    await ctx.send(f"Users that will use <{url}> will be {' '.join(roles)}")


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("disconnect")
async def disconnect_invite_from_role(ctx, url: str = None):
    invites = await get_sorted_invites(ctx)
    invites_urls = [_.url for _ in invites]
    if url:
        # validate url
        if url not in invites_urls:
            return await ctx.send("Invite url isn't valid")
        await bot.redis_client.hdel(INV_TO_ROLES, url)
        await ctx.send(f"Removed <{url}> invite")
    else:
        await ctx.send("Wrong syntax, `$invites.disconnect URL`")


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("stats_all")
async def get_all_invitations_stats(ctx):
    invites = await get_sorted_invites(ctx)
    widget = widget_builder(invites, display_all=True)
    await ctx.send(embed=widget)


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("stats_used")
async def get_invitations_stats(ctx):
    invites = await get_sorted_invites(ctx)
    widget = widget_builder(invites)
    await ctx.send(embed=widget)


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("help")
async def help(ctx):
    widget = Embed(description="Available commands for Invite-Role-Bot", color=0x03D692, title="Help")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    widget.add_field(name="$invites.stats_all", value="`Displays a list of all invite URLs`\n", inline=False)
    widget.add_field(
        name="$invites.stats_used", value="`Lists invite URLs which were used at least once`", inline=False
    )
    widget.add_field(name="$invites.list", value="`Lists all connected invite URLs and roles`", inline=False)
    widget.add_field(
        name="$invites.connect",
        value="`Connects an invite URL to roles, assigning roles to whoever joins using the given invite URL`",
        inline=False,
    )
    widget.add_field(
        name="$invites.disconnect",
        value="`Disconnects the given invite URL from roles it is connected to`",
        inline=False,
    )
    await ctx.send(embed=widget)


async def process_queue():
    # Invite A was used with 99.9% chance:
    #   1)
    #     A: 0 -> 1
    #     B: 0 -> 0
    #   2) There's a possibility that no invite was used
    #     A: none -> 1
    #     B: 0 -> 0
    #   3) There's a possibility that no invite was used
    #     A: 9 -> none
    #     B: 0 -> 0
    #
    # Can't confidently say what invite was used:
    #   1)
    #     A: 0 -> 1
    #     B: 0 -> 1
    #   2)
    #     A: none -> 1
    #     B: none -> 1
    #   3)
    #     A: 9 -> none
    #     B: 9 -> none
    #   4)
    #     A: 9 -> none
    #     B: none -> 1
    #
    # No invite was used:
    #   1) user joined through guild discovery or some other dark magic

    await bot.wait_until_ready()
    log_channel = bot.get_channel(config.LOG_CHANNEL_ID)

    while True:
        history_item = await bot.queue.get()
        logging.debug("have new items in the queue")
        old_invites_dict = {_.url: _.uses for _ in history_item["old_invites"]}
        new_invites_dict = {_.url: _.uses for _ in history_item["new_invites"]}
        delta = find_delta(old_invites_dict, new_invites_dict)
        member = history_item["user"]

        if delta.used:
            if len(delta.used) == 1 and not delta.removed:
                invite_link = [*delta.used][0]
                logging.debug(f"user ({member.mention}) on_join_sure1 {invite_link}")
                roles_to_assign = await get_roles_for_url(invite_link)
                await member.add_roles(*roles_to_assign)
            else:
                logging.debug(f"user ({member.mention}) on_join_unsure1 {[*delta.used]} | {delta.removed}")
                await log_channel.send(
                    f"Unsure about {member.mention}, possible invites: {[*delta.used]} | {delta.removed}"
                )
        elif delta.removed:
            # Not 100%, but close enough
            if len(delta.removed) == 1:
                invite_link = delta.removed[0]
                logging.debug(f"user ({member.mention}) on_join_sure2 {invite_link}")
                roles_to_assign = await get_roles_for_url(invite_link)
                await member.add_roles(*roles_to_assign)
            else:
                logging.debug(f"user ({member.mention}) on_join_unsure2 {delta.removed}")
                await log_channel.send(f"Unsure about {member.mention}, possible invites: {delta.removed}")
        else:
            logging.debug(f"user ({member.mention}) on_join_unsure3")
            await log_channel.send(
                f"Unsure about {member.mention}, user joined through guild discovery or some other dark magic"
            )


async def init_bot():
    await bot.wait_until_ready()
    logging.info(f"Logged in as {bot.user.name}")
    bot.old_invites = await bot.guilds[GUILD_INDEX].invites()


@bot.event
async def on_member_join(member: Member):
    # tasks that are waiting on the lock are added to a queue, and woken on a FIFO basis
    async with bot.lock:
        invites = await bot.guilds[GUILD_INDEX].invites()
        bot.queue.put_nowait({"old_invites": bot.old_invites, "new_invites": invites, "user": member})
        bot.old_invites = invites


if __name__ == "__main__":
    bot.lock = asyncio.Lock()  # init lock
    bot.queue = asyncio.Queue()  # init queue which will store list of [last_member_id: int, invites: List[Invite]]
    bot.loop.create_task(init_bot())
    bot.loop.create_task(process_queue())
    bot.redis_client = bot.loop.run_until_complete(aioredis.create_redis_pool(address=config.REDIS_HOST_URL))
    bot.run(config.TOKEN)
