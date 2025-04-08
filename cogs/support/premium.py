import discord
from discord.ext import commands, tasks
from discord import app_commands
import typing
import os
import datetime


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
        expiry_date = now + datetime.timedelta(days=30)  # Approximating a month as 30 days
    elif time == "3 months":
        expiry_date = now + datetime.timedelta(days=90)  # Approximating 3 months as 90 days
    elif time == "6 months":
        expiry_date = now + datetime.timedelta(days=180)  # Approximating 6 months as 180 days
    elif time == "1 year":
        expiry_date = now + datetime.timedelta(days=365)
    elif time == "lifetime":
        expiry_date = None  # Or a very distant date
    else:
        raise ValueError("Invalid time specified")
    return expiry_date


class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_premium_status.start()

    @commands.hybrid_group(
        name="premium",
        description="Premium commands"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.is_owner()
    async def premium(self, ctx):
        """Premium commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            return
        pass

    @premium.command(
        name="add",
        description="Add premium to a user or guild."
    )
    @commands.is_owner()
    async def add_premium(self, ctx, member: typing.Optional[typing.Union[discord.Member, discord.User]], guild: typing.Optional[str], time: typing.Literal["24 hours", "1 week", "2 weeks", "1 month", "3 months", "6 months", "1 year", "lifetime"], reason: str = "No reason provided"):
        """Add premium to a user or guild"""
        embed = discord.Embed(
            title="Premium Addition",
            colour=None
        )
        if member is None and guild is None:
            embed.description("Please specify either a member or a guild.")
            await ctx.send(embed=embed)
            return
        if member is not None and guild is not None:
            embed.description("Please specify either a member or a guild, not both.")
            await ctx.send(embed=embed)
            return

        target = member or guild
        if isinstance(target, str):
            target_id = target
            target_type = "guild"
        elif isinstance(target, (discord.Member, discord.User)):
            target_id = str(target.id)
            target_type = "user"
        else:
            embed.description("Please specify either a member or a guild, not both.")
            await ctx.send(embed=embed)
            return

        expiry_date = await calculate_expiry_date(time)

        # Prepare the data for the database
        premium_data = {
            "target_id": target_id,
            "target_type": target_type,
            "expiry_date": expiry_date,
            "reason": reason,
            "active": True
        }

        # Insert the premium data into the database
        existing_premium = self.bot.db.premium.find_one({"target_id": target_id})
        if existing_premium:
            embed.description(f"{target} already has premium.")
            await ctx.send(embed=embed)
            return

        try:
            self.bot.db.premium.insert_one(premium_data)
            embed = discord.Embed(
                title="Premium Added",
                description=f"Premium added to {target} for {time}.",
                colour=None
            )
            await ctx.send(embed=embed)
        except Exception:
            embed.description("An error occurred while adding premium.")
            await ctx.send(embed=embed)

    @premium.command(
        name="remove",
        description="Remove premium from a user or guild."
    )
    @commands.is_owner()
    async def remove_premium(self, ctx, member: typing.Optional[typing.Union[discord.Member, discord.User]], guild: typing.Optional[str]):
        """Remove premium from a user or guild"""
        embed = discord.Embed(
            title="Premium Removal",
            colour=None
        )
        if member is None and guild is None:
            embed.description("Please specify either a member or a guild.")
            await ctx.send(embed=embed)
            return
        if member is not None and guild is not None:
            embed.description("Please specify either a member or a guild, not both.")
            await ctx.send(embed=embed)
            return

        target = member or guild
        if isinstance(target, int):
            target_id = target

        elif isinstance(target, (discord.Member, discord.User)):
            target_id = str(target.id)
        else:
            embed.description("Invalid target type.")
            await ctx.send(embed=embed)
            return

        dbremove = self.bot.db.premium.find_one({"target_id": target_id})
        if not dbremove:
            embed = discord.Embed(
                title="Premium Not Found",
                description=f"{target} does not have premium.",
                colour=None
            )
            await ctx.send(embed=embed)
            return
        self.bot.db.premium.delete_one({"target_id": target_id})
        embed = discord.Embed(
            title="Premium Removed",
            description=f"{target} has been removed from premium.",
            colour=None
        )
        await ctx.send(embed=embed)

    @tasks.loop(hours=1)
    async def check_premium_status(self):
        """Check premium status and deactivate if expired."""
        now = datetime.datetime.now()
        expired_premiums = self.bot.db.premium.find({"expiry_date": {"$lt": now}, "active": True})
        async for premium in expired_premiums:
            await self.bot.db.premium.update_one({"_id": premium["_id"]}, {"$set": {"active": False}})
            target_id = premium["target_id"]
            target_type = premium["target_type"]
            print(f"Deactivated premium for {target_type} with ID {target_id} due to expiry.")

    @check_premium_status.before_loop
    async def before_check_premium_status(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Premium(bot))

