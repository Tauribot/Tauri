import discord
from discord.ext import commands
import os


async def isPremium(ctx):
    """Check if the user or their guild is a premium member"""
    # Check if the command is used in a guild or DM
    guild_id = getattr(ctx.guild, 'id', None)

    # Combined premium check for user and guild
    query = {"$or": [{"user_id": ctx.author.id}, {"guild_id": guild_id}]}
    premium_status = ctx.bot.db.premium.find_one(query)

    if premium_status and premium_status.get("active") is True:
        return True

    if premium_status and premium_status.get("active") is False:
        # If not premium, send a message and raise an exception
        blockedembed = discord.Embed(
            title="Premium Command",
            description="Seems like your premium has expired. If you believe this is a mistake, please contact support.",
            color=None
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Contact Support", url=os.getenv("support_url"), style=discord.ButtonStyle.link))

        await ctx.reply(embed=blockedembed, view=view, ephemeral=True)
        raise commands.DisabledCommand()

    # If not premium, send a message and raise an exception
    blockedembed = discord.Embed(
        title="Premium Command",
        description="Seems like this command is only available to premium servers. If you believe this is a mistake, please contact support.",
        color=None
    )
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Contact Support", url=os.getenv("support_url"), style=discord.ButtonStyle.link))
    await ctx.reply(embed=blockedembed, view=view, ephemeral=True)
    raise commands.DisabledCommand()