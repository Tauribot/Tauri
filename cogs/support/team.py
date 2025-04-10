import discord
from discord.ext import commands
from discord import app_commands
from internal.universal.premium import isPremium
from internal.universal.staff import staffroles
import time
import os


class DevCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ### Public Commands ###

    @commands.hybrid_command(name="ping", description="Check bot's latency")
    async def ping(self, ctx):
        start_time = time.time()
        message = await ctx.send("Testing ping...")
        end_time = time.time()

        embed = discord.Embed(
            title="Pong! 🏓",
            description=f"Bot Latency: {round((end_time - start_time) * 1000)}ms\nWebSocket: {round(self.bot.latency * 1000)}ms",
            color=None
        )

        await message.edit(content=None, embed=embed)
        
    ## Team Commands ##

    @commands.hybrid_command(
        name="toggle",
        description="Hide support roles."
    )
    @commands.has_role(1359893058447212574)
    async def hideroles(self, ctx):
        await ctx.defer(ephemeral=True)
        if self.bot.db.hiddenroles.find_one({"user_id": ctx.author.id}):
            for role in self.bot.db.hiddenroles.find_one({"user_id": ctx.author.id})["hidden_roles"]:
                await ctx.author.add_roles(role)
            await self.bot.db.hiddenroles.delete_one({"user_id": ctx.author.id})
            await ctx.send("Your roles have been given back.", ephemeral=True)
            return
        
        user_roles = ctx.author.roles
        staff_roles = [role.id for role in user_roles if role.id in staffroles]
        removed_roles = []
        if staff_roles:
            for role in staff_roles:
                await ctx.author.remove_roles(role)
                removed_roles.append(role)
        if removed_roles:
            await ctx.send(f"Removed {', '.join([self.bot.get_role(role).name for role in removed_roles])} from you.", ephemeral=True)
        else:
            await ctx.send("You don't have any support roles.", ephemeral=True)
            
        self.bot.db.hiddenroles.update_one(
            {"user_id": ctx.author.id},
            {"$set": {"hidden_roles": removed_roles}},
            upsert=True
        )
        

    ### Dev Commands ###

    devguild = int(1242439573254963292)

    @commands.hybrid_command(name="sync", description="Sync slash commands")
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
    @commands.is_owner()
    @app_commands.guilds(discord.Object(id=devguild))  # Dev Guild
    async def reload(self, ctx, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"Successfully reloaded cog: {cog}")
        except Exception as e:
            await ctx.send(f"Failed to reload cog: {e}")

async def setup(bot):
    await bot.add_cog(DevCommands(bot))
