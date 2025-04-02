import discord
from discord.ext import commands
import os

# Example use case:
# from handlers.premium import isPremium
# @commands.check(isPremium)

async def isPremium(ctx):
    """Check if the user is a premium member"""
    # Get guild ID safely
    guild_id = getattr(ctx.guild, 'id', None)

    # If no guild (DM context), check user premium status instead
    if guild_id is None:
        # For DMs, we could check user premium status
        blockedembed = discord.Embed(
            title="Guild-Only Command",
            description="This command can only be used in a server, not in DMs.",
            color=None
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Support", url=os.getenv("SUPPORT_URL")))
        await ctx.reply(embed=blockedembed, view=view, ephemeral=True)
        raise commands.NoPrivateMessage()

    # Normal guild premium check
    search = ctx.bot.db.premium.find_one({"guild_id": guild_id})
    if search is not None:
        return True
    else:
        blockedembed = discord.Embed(
            title="Premium Command",
            description="Seems like this command is only available to premium servers. If you believe this is a mistake, please contact support.",
            color=None
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Support", url=os.getenv("SUPPORT_URL")))
        await ctx.reply(embed=blockedembed, view=view, ephemeral=True)
        raise commands.DisabledCommand()