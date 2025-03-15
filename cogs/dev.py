import discord
from discord.ext import commands
from discord import app_commands
import time
import os

class DevCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        

    async def cog_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        cogs_dir = os.path.dirname(__file__)
        cogs = []
        
        for root, dirs, files in os.walk(cogs_dir):
            for file in files:
                if file.endswith('.py') and not file.startswith('_'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, cogs_dir)
                    cog_path = rel_path.replace(os.sep, '.')[:-3]
                    cogs.append(cog_path)
        
        return [
            app_commands.Choice(name=cog, value=cog)
            for cog in cogs if current.lower() in cog.lower()
        ]

    

    ### Public Commands ###

    @commands.hybrid_command(name="ping",description="Check bot's latency")
    async def ping(self, ctx):
        start_time = time.time()
        message = await ctx.send("Testing ping...")
        end_time = time.time()

        embed = discord.Embed(
            title="Pong! 🏓",
            description=f"Bot Latency: {round((end_time - start_time) * 1000)}ms\nWebSocket: {round(self.bot.latency * 1000)}ms",
            color=None
        )
        
        await message.edit(content=None,embed=embed)

    ### Dev Commands ###

    devguild = int(1242439573254963292)

    @commands.hybrid_command(name="sync",description="Sync slash commands")
    @commands.is_owner()
    @app_commands.guilds(discord.Object(id=devguild))  # Dev Guild
    async def sync(self, ctx):
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"Synced {len(synced)} command(s)")
        except Exception as e:
            await ctx.send(f"Failed to sync commands: {e}")

    @commands.hybrid_command(name="reload", description="Reload a cog")
    @app_commands.describe(cog="The cog to reload")
    @app_commands.autocomplete(cog=cog_autocomplete)
    @commands.is_owner()
    @app_commands.guilds(discord.Object(id=devguild))  # Dev Guild
    async def reload(self, ctx, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"Successfully reloaded cog: {cog}")
        except Exception as e:
            await ctx.send(f"Failed to reload cog: {e}")

    @commands.hybrid_command(
        name="shutdown",
        description="Shutdown the bot",
        aliases=["exit", "stop"],
    )
    @commands.is_owner()
    @app_commands.guilds(discord.Object(id=devguild))  # Dev Guild
    async def shutdown(self, ctx):
        await ctx.send("Shutting down...")
        exit()

async def setup(bot):
    await bot.add_cog(DevCommands(bot))
