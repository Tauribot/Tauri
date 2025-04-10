import discord
from discord.ext import commands, tasks
from discord import app_commands
import typing
import os
import datetime
from internal.universal.premium import calculate_expiry_date
import pymongo # Assuming pymongo, adjust if using a different driver
import asyncio

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ensure db connection is ready before starting the task
        if hasattr(self.bot, 'db') and self.bot.db is not None:
            self.check_premium_status.start()
        else:
            print("Database connection not ready, premium status check task not started.")
            # Optionally, implement a retry mechanism or wait until db is ready

    async def cog_unload(self):
        self.check_premium_status.cancel()

    async def _get_target_info(self, ctx, member: typing.Optional[typing.Union[discord.Member, discord.User]], guild_id_str: typing.Optional[str]) -> typing.Tuple[typing.Optional[str], typing.Optional[str], typing.Optional[typing.Union[discord.Member, discord.User, str]]]:
        """Helper to validate target and return target_id, target_type, and display target."""
        embed = discord.Embed(colour=discord.Colour.red()) # Default to error color

        if (member is None and guild_id_str is None) or (member is not None and guild_id_str is not None):
            embed.title = "Invalid Choice"
            embed.description = "Please specify either a member OR a guild ID, not both or neither."
            await ctx.send(embed=embed)
            return None, None, None

        target = member or guild_id_str
        target_id = None
        target_type = None

        if isinstance(target, str):
            # Basic validation for guild ID format, adjust if needed
            if not target.isdigit():
                 embed.title = "Invalid Guild ID"
                 embed.description = "The provided Guild ID is not valid."
                 await ctx.send(embed=embed)
                 return None, None, None
            target_id = target
            target_type = "guild"
            # Try to fetch guild for display name, optional
            try:
                guild_obj = self.bot.get_guild(int(target_id)) or await self.bot.fetch_guild(int(target_id))
                target = guild_obj.name if guild_obj else f"Guild ID: {target_id}"
            except (discord.NotFound, discord.Forbidden):
                 target = f"Guild ID: {target_id}" # Fallback if fetch fails
            except ValueError: # Handle non-integer guild_id_str if isdigit check fails somehow
                 embed.title = "Invalid Guild ID"
                 embed.description = "The provided Guild ID is not valid."
                 await ctx.send(embed=embed)
                 return None, None, None

        elif isinstance(target, (discord.Member, discord.User)):
            target_id = str(target.id)
            target_type = "user"
        else:
            # This case should ideally not be reached due to initial checks
            embed.title = "Invalid Target Type"
            embed.description = "An unexpected error occurred with the target type."
            await ctx.send(embed=embed)
            return None, None, None

        return target_id, target_type, target


    @commands.hybrid_group(
        name="premium",
        description="Premium commands"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.is_owner()
    async def premium(self, ctx):
        """Premium commands"""
        # Send help or overview if no subcommand is invoked
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)


    @premium.command(
        name="add",
        description="Add premium to a user or guild."
    )
    @app_commands.describe(
        member="The user to grant premium.",
        guild_id="The ID of the guild to grant premium.",
        time="Duration of the premium subscription.",
        reason="Reason for granting premium."
    )
    @commands.is_owner()
    async def add_premium(self, ctx, member: typing.Optional[typing.Union[discord.Member, discord.User]], guild_id: typing.Optional[str], time: typing.Literal["24 hours", "1 week", "2 weeks", "1 month", "3 months", "6 months", "1 year", "lifetime"], reason: str = "No reason provided"):
        """Add premium to a user or guild"""
        target_id, target_type, display_target = await self._get_target_info(ctx, member, guild_id)
        if not target_id:
            return # Error message already sent by helper

        embed = discord.Embed()

        # Check if premium already exists
        # Use count_documents for efficiency if just checking existence
        existing_premium_count = self.bot.db.premium.count_documents({"target_id": target_id, "active": True})
        if existing_premium_count > 0:
            embed.title = "Premium Already Exists"
            embed.description = f"{display_target} already has active premium."
            embed.colour = discord.Colour.orange()
            await ctx.send(embed=embed)
            return

        # Calculate the expiry date
        try:
            expiry_date = await calculate_expiry_date(time)
        except Exception as e: # Catch potential errors from calculation
             print(f"Error calculating expiry date: {e}")
             embed.title = "Calculation Error"
             embed.description = "Could not calculate the expiry date."
             embed.colour = discord.Colour.red()
             await ctx.send(embed=embed)
             return

        # Prepare the data for the database
        premium_data = {
            "target_id": target_id,
            "target_type": target_type,
            "expiry_date": expiry_date,
            "reason": reason,
            "added_by": str(ctx.author.id),
            "added_at": datetime.datetime.now(datetime.timezone.utc),
            "active": True
        }

        # Insert the premium data into the database
        try:
            # Consider using update_one with upsert=True if you want to overwrite inactive/non-existent
            # self.bot.db.premium.update_one({"target_id": target_id}, {"$set": premium_data}, upsert=True)
            self.bot.db.premium.insert_one(premium_data)
            embed.title = "Premium Added"
            embed.description = f"Premium added to {display_target} for **{time}**."
            embed.colour = discord.Colour.green()
            if expiry_date:
                 embed.add_field(name="Expires", value=discord.utils.format_dt(expiry_date, style='F'))
            else:
                 embed.add_field(name="Expires", value="Never (Lifetime)")
            await ctx.send(embed=embed)
        except pymongo.errors.PyMongoError as e: # Catch specific DB errors
            print(f"Database error adding premium: {e}")
            embed.title = "Database Error"
            embed.description = "An error occurred while adding premium to the database."
            embed.colour = discord.Colour.red()
            await ctx.send(embed=embed)
        except Exception as e: # Catch other unexpected errors
            print(f"Unexpected error adding premium: {e}")
            embed.title = "Error"
            embed.description = "An unexpected error occurred while adding premium."
            embed.colour = discord.Colour.red()
            await ctx.send(embed=embed)


    @premium.command(
        name="remove",
        description="Remove premium from a user or guild."
    )
    @app_commands.describe(
        member="The user to remove premium from.",
        guild_id="The ID of the guild to remove premium from."
    )
    @commands.is_owner()
    async def remove_premium(self, ctx, member: typing.Optional[typing.Union[discord.Member, discord.User]], guild_id: typing.Optional[str]):
        """Remove premium from a user or guild"""
        target_id, _, display_target = await self._get_target_info(ctx, member, guild_id)
        if not target_id:
            return # Error message already sent by helper

        embed = discord.Embed()

        # Remove premium - delete_one returns info about the deletion
        try:
            result = self.bot.db.premium.delete_one({"target_id": target_id})

            if result.deleted_count > 0:
                embed.title = "Premium Removed"
                embed.description = f"Premium access has been removed from {display_target}."
                embed.colour = discord.Colour.green()
            else:
                embed.title = "Premium Not Found"
                embed.description = f"{display_target} does not seem to have premium."
                embed.colour = discord.Colour.orange()
            await ctx.send(embed=embed)

        except pymongo.errors.PyMongoError as e: # Catch specific DB errors
            print(f"Database error removing premium: {e}")
            embed.title = "Database Error"
            embed.description = "An error occurred while removing premium from the database."
            embed.colour = discord.Colour.red()
            await ctx.send(embed=embed)
        except Exception as e: # Catch other unexpected errors
            print(f"Unexpected error removing premium: {e}")
            embed.title = "Error"
            embed.description = "An unexpected error occurred while removing premium."
            embed.colour = discord.Colour.red()
            await ctx.send(embed=embed)


    ### Hourly Subcription Status Check ###

    @tasks.loop(hours=1)
    async def check_premium_status(self):
        """Check premium status and deactivate if expired."""
        now = datetime.datetime.now(datetime.timezone.utc) # Use timezone-aware datetime

        query = {
            "expiry_date": {"$lt": now, "$ne": None}, # Find expired (less than now, and not None for lifetime)
            "active": True
        }
        update = {"$set": {"active": False}}

        try:
            result = self.bot.db.premium.update_many(query, update)
            if result.modified_count > 0:
                print(f"Deactivated {result.modified_count} expired premium subscriptions.")
        except pymongo.errors.PyMongoError as e:
            print(f"Database error during premium status check: {e}")
        except Exception as e:
             print(f"Unexpected error during premium status check: {e}")


    @check_premium_status.before_loop
    async def before_check_premium_status(self):
        await self.bot.wait_until_ready()
        # Add a check for db connection here too, if it might not be ready yet
        while not hasattr(self.bot, 'db') or self.bot.db is None:
             print("Waiting for database connection before starting premium check loop...")
             await asyncio.sleep(5) # Wait 5 seconds before checking again


async def setup(bot):
    # Ensure the cog is added only after the bot is ready and potentially db is connected
    # Depending on your bot structure, you might need to await db connection setup first
    await bot.add_cog(Premium(bot))

