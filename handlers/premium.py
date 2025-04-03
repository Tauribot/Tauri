import discord
from discord.ext import commands
import os


async def isPremium(ctx):
    """Check if the user or their guild is a premium member"""
    # Check if the command is used in a guild or DM
    guild_id = getattr(ctx.guild, 'id', None)

    # Prepare the query to find premium status
    query = {}
    premium_user = False
    premium_guild = False

    if guild_id is not None:
        premium_guild_data = ctx.bot.db.premium.find_one({"target_id": guild_id, "target_type": "guild", "active": True})
        if premium_guild_data:
            premium_guild = True

    premium_user_data = ctx.bot.db.premium.find_one({"target_id": ctx.author.id, "target_type": "user", "active": True})
    if premium_user_data:
        premium_user = True

    if premium_user or premium_guild:
        return True

    # If not premium, send a message and raise an exception
    blockedembed = discord.Embed(
        title="Premium Command",
        description="Seems like this command is only available to premium servers. If you believe this is a mistake, please contact support.",
        color=None
    )
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Contact Support", url=os.getenv("SUPPORT_URL"), style=discord.ButtonStyle.link))
    await ctx.reply(embed=blockedembed, view=view, ephemeral=True)
    raise commands.DisabledCommand()