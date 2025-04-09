from re import search
from discord.ext import tasks
import discord
from discord.ext import commands
from discord import app_commands
from roblox import Client, AvatarThumbnailType
from roblox.utilities.exceptions import UserNotFound
from internal.support.blacklisting import can_blacklist
import typing
import os
import re

class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.task_clear = self.clear_recently_joined.start()
        self.support_url = os.getenv("support_url")
        self.support_id = [1242439573254963292,]
        self.recently_joined = []

    @commands.Cog.listener()
    async def on_cog_unload(self, cog):
        if cog == self:
            self.task_clear.cancel()

    @tasks.loop(seconds=3600)
    async def clear_recently_joined(self):
        self.recently_joined = []

    ### Handle Guild Blacklist ###
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Check if the guild is blacklisted"""

        if guild.id in self.recently_joined:
            return

        user_record = self.bot.db.blocklist.find_one({"user_id": guild.owner.id})
        guild_record = self.bot.db.guildstatus.find_one({"guild_id": guild.id})

        if guild_record or user_record:
            try:
                blockedembed = discord.Embed(
                    title="Guild Access Revoked",
                    description=f"Your server `{guild.name}` is not eligible to use our service due to a violation of our Terms of Service. If you believe this is a mistake, please contact support.",
                    colour=None
                )
                view = discord.ui.View(timeout=None)
                view.add_item(discord.ui.Button(label="Support", url=self.support_url))

                await guild.owner.send(embed=blockedembed, view=view)
            except discord.Forbidden:
                pass

            try:
                self.recently_joined.append(guild.id)
                await guild.leave()
            except Exception as e:
                print(f"Failed to leave {guild.name}: {e}")

    

    ### Blacklist Commands ###
    @commands.hybrid_group(
        name="blacklist",
        description="Blacklist commands"
    )
    @commands.is_owner()
    @app_commands.guilds(discord.Object(id=int(1242439573254963292))) # Dev Guild
    async def blacklist(self, ctx):
        """Blacklist commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            return


    @blacklist.command(
        name="guild",
        description="Blacklist a guild"
    )
    async def bl_guild(self, ctx, guild: int):
        """Blacklist a guild"""
        guild_id = str(guild)

        initial = self.bot.db.guildstatus.find_one({"guild_id": guild_id})

        if initial:
            self.bot.db.guildstatus.delete_one({"_id": initial["_id"]})
            await ctx.send(f"Guild (`{guild_id}`) is now no longer blacklisted.")
        else:
            self.bot.db.guildstatus.insert_one({
                "guild_id": guild_id,
                "blacklisted": True
            })
            await ctx.send(f"Guild (`{guild_id}`) is now blacklisted.")


    @blacklist.command(
        name="add",
        description="Blacklist a user"
    )
    @commands.check(can_blacklist)
    async def add(self, ctx, user: typing.Union[discord.Member, discord.User], *, reason: str = "No reason provided"):
        """Blacklist a user"""

        staffid = str(ctx.author.id)
        userid = str(user.id)

        self.bot.db.blocklist.insert_one({
            "user_id": userid,
            "reason": reason,
            "staff_id": staffid,
            "timestamp": discord.utils.utcnow().isoformat()
        })

        embed = discord.Embed(
            title="User Blocked",
            description=f"{user} ({userid}) has been blacklisted for `{reason}`.",
            colour=None
        )
        await ctx.reply(embed=embed)


    @blacklist.command(
        name="remove",
        description="Remove a user from the blacklist"
    )
    @commands.check(can_blacklist)
    async def remove(self, ctx, user: typing.Union[discord.Member, discord.User]):
        """Remove a user from the blacklist"""

        userid = str(user.id)

        self.bot.db.blocklist.delete_one({"user_id": userid})

        embed = discord.Embed(
            title="Block Removed",
            description=f"{user} ({userid}) has been removed from the blocklist.",
            colour=None
        )

        await ctx.reply(embed=embed)

    @blacklist.command(
        name="edit",
        description="Edit a user's block reason"
    )
    @commands.check(can_blacklist)
    async def edit(self, ctx, user: typing.Union[discord.Member, discord.User], *, reason: str = "No reason provided"):
        """Edit a user's blacklist reason"""
        
        userid = str(user.id)

        if not self.bot.db.blocklist.find_one({"user_id": userid}):
            await ctx.send("User is not blocked.")
            return

        self.bot.db.blocklist.update_one(
            {"user_id": userid},
            {"$set": {"reason": reason}}
        )

        embed = discord.Embed(
            title="Block Edited",
            description=f"{user} ({userid}) has been updated with the following reason: {reason}",
            colour=None
        )

        await ctx.reply(embed=embed)

    @blacklist.command(
        name="review",
        description="Review a user's block status"
    )
    @commands.check(can_blacklist)
    async def review(self, ctx, user: typing.Union[discord.Member, discord.User]):
        """Review a user's blacklist status"""

        userid = str(user.id)
        blacklist = self.bot.db.blocklist.find_one({"user_id": userid})

        if not blacklist:
            await ctx.send("User is not blocked.")
            return

        embed = discord.Embed(
            title="Blacklist Review",
            description=f"{user} ({userid}) is blocked for the following reason: {blacklist['reason']}",
            colour=None
        )

        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Blacklist(bot))