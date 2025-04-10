import discord
from discord.ext import commands, tasks
from discord import app_commands
import typing
import os
import datetime
from internal.universal.premium import calculate_expiry_date

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_premium_status.start()

    async def cog_unload(self):
        self.check_premium_status.cancel()

    @commands.hybrid_group(
        name="premium",
        description="Premium commands"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.is_owner()
    async def premium(self, ctx):
        """Premium commands"""
        pass

    @premium.command(
        name="add",
        description="Add premium to a user or guild."
    )
    @commands.is_owner()
    async def add_premium(self, ctx, member: typing.Optional[typing.Union[discord.Member, discord.User]], guild: typing.Optional[str], time: typing.Literal["24 hours", "1 week", "2 weeks", "1 month", "3 months", "6 months", "1 year", "lifetime"], reason: str = "No reason provided"):
        """Add premium to a user or guild"""

        embed = discord.Embed(
            colour=None
        )

        # Condition to check if either member or guild is provided
        if member is None and guild is None or member is not None and guild is not None:
            embed.title("Invalid Choice")
            embed.description("Please specify either a member or a guild, not both.")
            await ctx.send(embed=embed)
            return

        # Condition to check if either member or guild is provided
        target = member or guild
        if isinstance(target, str):
            target_id = target
            target_type = "guild"
        elif isinstance(target, (discord.Member, discord.User)):
            target_id = str(target.id)
            target_type = "user"
        else:
            embed.title("Invalid Target")
            embed.description("Please specify either a member or a guild.")
            await ctx.send(embed=embed)
            return

        # Calculate the expiry date
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
            embed.title("Premium Already Exists")
            embed.description(f"{target} already has premium.")
            await ctx.send(embed=embed)
            return

        # Insert the premium data into the database
        try:
            self.bot.db.premium.insert_one(premium_data)
            embed.title("Premium Added")
            embed.description(f"Premium added to {target} for {time}.")
            await ctx.send(embed=embed)
        except Exception:
            embed.title("Error")
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
            colour=None
        )

        # Condition to check if either member or guild is provided
        if member is None and guild is None or member is not None and guild is not None:
            embed.title("Invalid Choice")
            embed.description("Please specify either a member or a guild, not both.")
            await ctx.send(embed=embed)
            return

        #    Condition to check if either member or guild is provided
        target = member or guild
        if isinstance(target, int):
            target_id = target

        elif isinstance(target, (discord.Member, discord.User)):
            target_id = str(target.id)
        else:
            embed.description("Invalid target type.")
            await ctx.send(embed=embed)
            return
        
        # Check if the target has premium

        dbremove = self.bot.db.premium.find_one({"target_id": target_id})
        if not dbremove:
            embed.title("Premium Not Found")
            embed.description(f"{target} does not have premium.")
            await ctx.send(embed=embed)
            return
        
        # Remove premium
        self.bot.db.premium.delete_one({"target_id": target_id})
        embed.title("Premium Removed")
        embed.description(f"{target} has been removed from premium.")
        await ctx.send(embed=embed)


    ### Hourly Subcription Status Check ###

    @tasks.loop(hours=1)
    async def check_premium_status(self):
        """Check premium status and deactivate if expired."""
        
        # Get time
        now = datetime.datetime.now()

        # Find expired premium
        expired_premiums = self.bot.db.premium.find({"expiry_date": {"$lt": now}, "active": True})

        # Deactivate expired premium
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

