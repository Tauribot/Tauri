import discord
from discord.ext import commands
import os
import datetime
from internal.universal.emojis import getemojis

async def calculate_expiry_date(time: str) -> datetime.datetime:
    """Calculate the expiry date based on the given time string."""
    now = datetime.datetime.now()
    if time == "24 hours":
        expiry_date = now + datetime.timedelta(hours=24)
    elif time == "1 week":
        expiry_date = now + datetime.timedelta(weeks=1)
    elif time == "2 weeks":
        expiry_date = now + datetime.timedelta(weeks=2)
    elif time == "1 month":
        expiry_date = now + datetime.timedelta(days=30)
    elif time == "3 months":
        expiry_date = now + datetime.timedelta(days=90)
    elif time == "6 months":
        expiry_date = now + datetime.timedelta(days=180)
    elif time == "1 year":
        expiry_date = now + datetime.timedelta(days=365)
    elif time == "lifetime":
        expiry_date = None
    else:
        raise ValueError("Invalid time specified")
    return expiry_date

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

    if ctx.author.id:
        target = str(ctx.author.id)

    premium_user_data = ctx.bot.db.premium.find_one({"target_id": target, "target_type": "user", "active": True})
    if premium_user_data:
        premium_user = True

    if premium_user or premium_guild:
        return True
    
    emojis = await getemojis()
    premium_emoji = emojis.get("premium")

    # If not premium, send a message and raise an exception
    print(ctx.command.qualified_name)
    
    blockedembed = discord.Embed(
        title=f"{premium_emoji} Premium Command",
        description="Seems like this command is only available to premium servers. If you believe this is a mistake, please contact support.",
        color=None
    )
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Contact Support", url=os.getenv("SUPPORT_URL"), style=discord.ButtonStyle.link))
    await ctx.reply(embed=blockedembed, view=view, ephemeral=True)
    raise commands.DisabledCommand()