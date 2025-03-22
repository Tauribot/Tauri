import discord
from discord.ext import commands

import os
import sentry_sdk

class logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_error(self, event, *args):
        """Handle errors that occur in the error handler itself"""
        error = args[0] if args else None
        
        with sentry_sdk.new_scope() as scope:
            scope.level = "fatal"
            scope.set_tag("error_handler", "True")
            scope.set_extra("event", event)
            event_id = sentry_sdk.capture_exception(error)
            short_id = event_id[:8]
            
            embed = discord.Embed(
                title="A critical error occurred",
                description="A critical error occurred in the error handler. Please report this to the developers.",
                color=discord.Color.dark_red()
            )
            if os.getenv("environment") == "development":
                embed.add_field(name="Error", value=f"```{error}```")
            embed.set_footer(text=f"Error ID: {short_id}")
            
            try:
                self.bot.db.errors.insert_one({
                    "event": event,
                    "error_handler": True,
                    "short_id": short_id,
                    "event_id": event_id,
                    "error": str(error),
                    "timestamp": discord.utils.utcnow().isoformat()
                })
            except Exception as e:
                print(f"Failed to log error to database: {e}")
            
            criticalerror = discord.Embed(
                title="Critical Error Handler Failure",
                description=f"Event: {event}\nError Handler: True\nShort ID: {short_id}",
                color=discord.Color.dark_red()
            )
            
            criticalerror.add_field(name="Error", value=f"```py\n{error}\n```")
            criticalerror.set_footer(text=f"Error ID: {event_id}")
            
            try:
                channelid = os.getenv("errors")
                errorlogs = self.bot.get_channel(int(channelid))
                
                if errorlogs:
                    await errorlogs.send(embed=criticalerror)
                else:
                    print("Error logs channel not found")
            except Exception as e:
                print(f"Failed to send error log: {e}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        embed = discord.Embed(title="Oops!", color=discord.Color.red())

        if isinstance(error, commands.MissingRequiredArgument):
            embed.description = f"Missing required argument: `{error.param.name}`"
        elif isinstance(error, commands.CheckFailure):
            embed.description = "You do not have permission to use this command"
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            embed.description = "I don't have the required permissions to do that!"
        elif isinstance(error, commands.BotMissingPermissions):
            embed.description = "I don't have the required permissions to do that!"
        elif isinstance(error, commands.CommandOnCooldown):
            embed.description = f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds"
        elif isinstance(error, commands.DisabledCommand):
            embed.description = "This command is currently disabled"
        elif isinstance(error, commands.NoPrivateMessage):
            embed.description = "This command can't be used in private messages"
        else:
            error = getattr(error, 'original', error)
            with sentry_sdk.new_scope() as scope:
                scope.level = "error"
                scope.set_user({
                    "id": ctx.author.id,
                    "username": str(ctx.author),
                    "command": ctx.command.name if ctx.command else "Unknown"
                })
                scope.set_extra("guild_id", ctx.guild.id if ctx.guild else None)
                scope.set_extra("channel_id", ctx.channel.id)
                event_id = sentry_sdk.capture_exception(error)
                short_id = event_id[:8]

                embed.description = f"An error occurred while executing the command. Please try again later.\nError ID: `{short_id}`"
                if os.getenv("environment") == "development":
                    embed.add_field(name="Error", value=f"```{error}```")

                try:
                    self.bot.db.errors.insert_one({
                        "user": ctx.author.id,
                        "command": ctx.command.qualified_name if ctx.command else "Unknown",
                        "guild": ctx.guild.id if ctx.guild else None,
                        "channel": ctx.channel.id,
                        "short_id": short_id,
                        "event_id": event_id,
                        "error": str(error),
                        "timestamp": discord.utils.utcnow().isoformat()
                    })
                except Exception as e:
                    print(f"Failed to log error to database: {e}")

                logembed = discord.Embed(
                    title="Error Logging",
                    description=f"* User: {ctx.author} ({ctx.author.id})\n"
                                f"* Command: {ctx.command.qualified_name if ctx.command else 'Unknown'}\n"
                                f"* Guild: {ctx.guild.id if ctx.guild else 'N/A'}\n"
                                f"* Short ID: {short_id}\n"
                                f"* Event ID: {event_id}\n",
                    color=discord.Color.red()
                )
                logembed.add_field(name="Error", value=f"```{error}```")
                logembed.set_footer(text=f"Error ID: {event_id}")

                try:
                    channelid = os.getenv("errors")
                    errorlogs = self.bot.get_channel(int(channelid))
                    if errorlogs:
                        await errorlogs.send(embed=logembed)
                    else:
                        print("Error logs channel not found")
                except Exception as e:
                    print(f"Failed to send error log: {e}")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(logs(bot))