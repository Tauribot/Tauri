import discord
from discord.ext import commands
from discord import app_commands
import typing
from handlers.premium import isPremium
import os
from handlers.emojis import getemojis

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(
        name="premium",
        description="Premium commands"
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.guilds(discord.Object(id=int(1242439573254963292)))
    async def premium(self, ctx):
        pass

async def setup(bot):
    await bot.add_cog(Premium(bot))