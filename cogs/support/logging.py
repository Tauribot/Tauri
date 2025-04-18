import discord
from discord.ext import commands, tasks

import os
import sentry_sdk
import requests

class logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.heartbeat.start()
        self.link = "https://sm.hetrixtools.net/hb/?s=e7905883851df790e2ff23c073c267bd"
    
    
    @tasks.loop(seconds=60)
    async def heartbeat(self):
        try:
            requests.get(self.link, timeout=10)
        except Exception as e:
            print(f"Failed to send heartbeat: {e}")
        
        

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
            return
        elif isinstance(error, commands.DisabledCommand):
            return
        elif isinstance(error, commands.NoPrivateMessage):
            return
        else:
            # Get the original error
            error = getattr(error, 'original', error)

            # Set the scope level to error
            with sentry_sdk.new_scope() as scope:
                scope.level = "error"
                scope.set_user({
                    "id": ctx.author.id,
                    "username": str(ctx.author),
                    "command": ctx.command.name if ctx.command else "Unknown"
                })

                # Set the extra to the guild id and channel id
                scope.set_extra("guild_id", ctx.guild.id if ctx.guild else None)
                scope.set_extra("channel_id", ctx.channel.id)

                # Capture the exception
                event_id = sentry_sdk.capture_exception(error)

                # Set the short id to the first 8 characters of the event id
                short_id = event_id[:8]

                # Set the embed description to the error message
                embed.description = f"An error occurred while executing the command. Please try again later.\nError ID: `{short_id}`"

                # If the environment is development, add the error to the embed
                if os.getenv("environment") == "development":
                    embed.add_field(name="Error", value=f"```{error}```")

                # Try to insert the error into the database
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

                # Create the error logging embed
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

                    # If the error logs channel is found, send the embed
                    if errorlogs:
                        await errorlogs.send(embed=logembed)
                    else:
                        print("Error logs channel not found")
                except Exception as e:
                    print(f"Failed to send error log: {e}")

        # Send the embed to the user
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(logs(bot))