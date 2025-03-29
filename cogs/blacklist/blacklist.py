from re import search
from discord.ext import tasks
import discord
from discord.ext import commands
from discord import app_commands
from roblox import Client, AvatarThumbnailType
from roblox.utilities.exceptions import UserNotFound
import typing
import os
import re

class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.support_url = "https://support.example.com"
        self.support_id = [1242439573254963292, 0]

    ### Handle Guild Blacklist ###
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Check if the guild is blacklisted"""

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
                await guild.leave()
            except Exception as e:
                print(f"Failed to leave {guild.name}: {e}")

    ### Blacklist Commands ###

    @commands.hybrid_group(
        name="blacklist",
        description="Blacklist commands"
    )
    @commands.has_role("Blacklist Manager")
    @app_commands.guilds(discord.Object(id=int(1242439573254963292))) # Dev Guild
    async def blacklist(self, ctx):
        pass


    @blacklist.command(
        name="guild",
        description="Blacklist a guild"
    )
    async def bl_guild(self, ctx, guild: int):
        """Blacklist a guild"""
        guild_id = int(str(guild))

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
    async def add(self, ctx, user: typing.Union[discord.Member, discord.User], *, reason: str = "No reason provided"):
        """Blacklist a user"""

        pretest = await can_blacklist(ctx, user)
        if pretest is False:
            return

        self.bot.db.blocklist.insert_one({
            "user_id": user.id,
            "reason": reason,
            "staff_id": ctx.author.id,
            "timestamp": discord.utils.utcnow().isoformat()
        })

        embed = discord.Embed(
            title="User Blocked",
            description=f"{user} ({user.id}) has been blacklisted for `{reason}`.",
            colour=None
        )
        await ctx.reply(embed=embed)


    @blacklist.command(
        name="remove",
        description="Remove a user from the blacklist"
    )
    async def remove(self, ctx, user: typing.Union[discord.Member, discord.User]):
        """Remove a user from the blacklist"""

        if not user:
            await ctx.send("User not found")
            return

        self.bot.db.blocklist.delete_one({"user_id": user.id})

        embed = discord.Embed(
            title="Block Removed",
            description=f"{user} ({user.id}) has been removed from the blocklist.",
            colour=None
        )

        await ctx.reply(embed=embed)

    @blacklist.command(
        name="edit",
        description="Edit a user's block reason"
    )
    async def edit(self, ctx, user: typing.Union[discord.Member, discord.User], *, reason: str = "No reason provided"):
        """Edit a user's blacklist reason"""

        if not user:
            await ctx.send("User not found")
            return

        if not self.bot.db.blocklist.find_one({"user_id": user.id}):
            await ctx.send("User is not blocked.")
            return

        self.bot.db.blocklist.update_one(
            {"user_id": user.id},
            {"$set": {"reason": reason}}
        )

        embed = discord.Embed(
            title="Block Edited",
            description=f"{user} ({user.id}) has been updated with the following reason: {reason}",
            colour=None
        )

        await ctx.reply(embed=embed)

    @blacklist.command(
        name="review",
        description="Review a user's block status"
    )
    async def review(self, ctx, user: typing.Union[discord.Member, discord.User]):
        """Review a user's blacklist status"""

        if not user:
            await ctx.send("User not found")
            return

        blacklist = self.bot.db.blocklist.find_one({"user_id": user.id})

        if not blacklist:
            await ctx.send("User is not blocked.")
            return

        embed = discord.Embed(
            title="Blacklist Review",
            description=f"{user} ({user.id}) is blocked for the following reason: {blacklist['reason']}",
            colour=None
        )

        await ctx.reply(embed=embed)

async def can_blacklist(ctx, user):
    failure = discord.Embed(
        title="Block Failed",
        description=f"Failed to block {user} ({user.id})",
        colour=None
    )

    if not user:
        failure.description = f"{failure.description}\n```User not found```"
        await ctx.send(embed=failure)
        return False

    if any(role.name == "Blacklist Manager" for role in user.roles):
        failure.description = f"{failure.description}\n```Cannot blacklist a Blacklist Manager```"
        await ctx.send(embed=failure)
        return False

    if any(role.name == "Support Team" for role in user.roles):
        failure.description = f"{failure.description}\n```Cannot blacklist a Support Team member```"
        await ctx.send(embed=failure)
        return False

    if user.id == ctx.author.id:
        failure.description = f"{failure.description}\n```Cannot blacklist yourself```"
        await ctx.send(embed=failure)
        return False

    if user.id == ctx.bot.user.id:
        failure.description = f"{failure.description}\n```Cannot blacklist myself```"
        await ctx.send(embed=failure)
        return False

    return True

async def setup(bot):
    await bot.add_cog(Blacklist(bot))