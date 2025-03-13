import discord
import asyncio
import pymongo
from dotenv import load_dotenv
from itertools import cycle
from discord.ext import commands, tasks
import pymongo.database
import sentry_sdk
from sentry_sdk import push_scope, capture_exception
from sentry_sdk.integrations.pymongo import PyMongoIntegration
import os
import jishaku
from infisical_sdk import InfisicalSDKClient

load_dotenv()

bot = commands.Bot(command_prefix=commands.when_mentioned_or('>'), intents=discord.Intents.all())

async def setup_database():
    """Initialize database connection"""
    bot.cluster = pymongo.MongoClient(os.getenv("mongourl"))
    if os.getenv("environment") == "development":
        bot.db = pymongo.database.Database(bot.cluster, "cognition-dev")
    elif os.getenv("environment") == "production":
        bot.db = pymongo.database.Database(bot.cluster, "cognition")
    if bot.db is not None:
        print("Connected to the database")
    return bot.db is not None

@bot.event 
async def on_ready():
    await bot.change_presence(status=discord.Status.dnd)
    print(f"Logged in as {bot.user}")
    
    
# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required argument")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command")
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds")
    elif isinstance(error, commands.CommandInvokeError):
        with sentry_sdk.new_scope() as scope:
            scope.level = "error"
            scope.set_user({"id": ctx.author.id, "username": str(ctx.author), "command": ctx.command.name })
            event_id = sentry_sdk.capture_exception(error)
            short_id = event_id[:8]
            
            embed = discord.Embed(
                title="An error occurred",
                description=f"An error occurred while executing the command. Please try again later.",
                color=discord.Color.red()
            )
            if os.getenv("environment") == "development":
                embed.add_field(name="Error", value=f"```{error}```")
            embed.set_footer(text=f"Error ID: {short_id}")
            
            bot.db.errors.insert_one({
                "user": ctx.author.id,
                "command": ctx.command.name,
                "guild": ctx.guild.id,
                "channel": ctx.channel.id,
                "short_id": short_id,
                "event_id": event_id,
                "error": str(error)
            })
            
            logembed = discord.Embed(
                title="New User Error",
                description=f"User: {ctx.author} ({ctx.author.id})\nCommand: {ctx.command.name}\nGuild: {ctx.guild.name} ({ctx.guild.id})\nChannel: {ctx.channel.name} ({ctx.channel.id})\nShort ID: {short_id}",
                color=discord.Color.red()
            )
            if os.getenv("environment") == "development":
                logembed.add_field(name="Error", value=f"```{error}```")
            
            logembed.set_footer(text=f"Error ID: {event_id}")
            errorlogs = bot.get_channel(1349454868955271290)
            
            await errorlogs.send(embed=logembed)
            await ctx.send(embed=embed)
            
async def secrets():
    client = InfisicalSDKClient(host="https://app.infisical.com")

    slug = None

    if os.getenv("environment") == "development":
        slug = "dev"
    elif os.getenv("environment") == "production":
        slug = "prod"

    else:
        raise Exception("Invalid environment")

    client.auth.universal_auth.login(
        client_id=os.getenv("vaultid"), 
        client_secret=os.getenv("vaultsecret")
    )

    token = client.secrets.get_secret_by_name(secret_name="token", project_id="1fc23486-c8b2-4135-a02a-a40be32b3d65", environment_slug=slug, secret_path="/")
    mongourl = client.secrets.get_secret_by_name(secret_name="mongourl", project_id="1fc23486-c8b2-4135-a02a-a40be32b3d65", environment_slug=slug, secret_path="/")

    os.environ["token"] = token.secretValue
    os.environ["mongourl"] = mongourl.secretValue

    if token.secretValue and mongourl.secretValue:
        return True
    else:
        return False

# Load all cogs
    
async def load():
    """Load Secrets"""
    await secrets()
    """Load extensions after ensuring database is ready"""
    if not await setup_database():
        raise RuntimeError("Failed to connect to database")
        
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded {filename[:-3]}')
            except Exception as e:
                print(f'Failed to load {filename[:-3]}: {str(e)}')

    for folder in os.listdir('./cogs'):
        if os.path.isdir(f'./cogs/{folder}'):
            for filename in os.listdir(f'./cogs/{folder}'):
                if filename.endswith('.py'):
                    try:
                        await bot.load_extension(f'cogs.{folder}.{filename[:-3]}')
                        print(f'Loaded {filename[:-3]}')
                    except Exception as e:
                        print(f'Failed to load {filename[:-3]}: {str(e)}')

async def main():
    async with bot:
        if os.getenv("environment") == "production":
            sentry_sdk.init(
                dsn="https://53a4e9de4624e66e7a499fb8f849d2db@o4508875710136320.ingest.us.sentry.io/4508875712233472",
                traces_sample_rate=1.0,
                integrations=[PyMongoIntegration()],
                _experiments={
                    "profiles_sample_rate": 1.0,
                },
            )
            
        try:
            await load()
            await bot.load_extension("jishaku")
        except Exception as e:
            print(f"Error during startup: {str(e)}")
            return
            
        token = os.getenv("token")
        if not token:
            print("Error: 'token' environment variable not set.")
            return
        
        await bot.start(token)

asyncio.run(main())

