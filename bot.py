from discord.ext import commands
import discord
from discord import Member, Embed
from config import TOKEN
import logging

# initialize bot params
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="$invites.", intents=intents)

# setup logger
logging.basicConfig(filename="eco-memes.log", level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s:%(message)s")


async def get_sorted_invites(ctx):
    guild = bot.get_guild(ctx.guild.id)
    invites = await guild.invites()
    sorted_invites = sorted(invites, key=lambda x: x.uses, reverse=True)
    return sorted_invites


def widget_builder(invites, all=False):
    description_all = "Statistics for all links"
    description_uses = "Statistics for links with uses"
    description = description_all if all else description_uses

    widget = discord.Embed(
        description=description, color=0x03d692, title="Invitations Stats")
    widget.set_author(name=bot.user.name)
    widget.set_thumbnail(
        url="https://pbs.twimg.com/profile_images/1366064859574661124/Ocl4oSnU_400x400.jpg")  # TODO fix to .png
    widget.set_footer(text="FooterText")
    for i in invites:
        if i.uses == 0 and all == False:
            continue
        widget.add_field(
            name=f"{i.code}",
            value=f"Created by: {i.inviter.mention}\nUses: `{i.uses}`\nLink: {i.url}", inline=False)
    return widget


@commands.has_any_role('Eco Team')
@bot.command('stats_all')
async def get_all_invitations_stats(ctx):
    invites = await get_sorted_invites(ctx)
    widget = widget_builder(invites, all=True)
    await ctx.send(embed=widget)


@commands.has_any_role('Eco Team')
@bot.command('stats_uses')
async def get_invitations_stats(ctx):
    invites = await get_sorted_invites(ctx)
    widget = widget_builder(invites)
    await ctx.send(embed=widget)


@bot.event
async def on_member_join(member: Member):
    print(member)  # TODO process event

if __name__ == "__main__":
    # bot.loop.create_task(fetch())
    bot.run(TOKEN)
