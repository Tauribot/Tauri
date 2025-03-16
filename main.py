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
if os.getenv("environment") == "development":
    bot = commands.Bot(command_prefix=commands.when_mentioned_or('>'), intents=discord.Intents.all())
elif os.getenv("environment") == "production":
    bot = commands.Bot(command_prefix=commands.when_mentioned_or('-'), intents=discord.Intents.all())


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

@bot.before_invoke
async def before_invoke(ctx):
    bot.db.commands.insert_one({
        "username": ctx.author.name,
        "userid": ctx.author.id,
        "command": ctx.command.qualified_name,
        "guild": ctx.guild.id if ctx.guild else None,
        "channel": ctx.channel.id
    })
            
async def secrets():
    client = InfisicalSDKClient(host="https://secrets.jadyn.au")

    slug = None
    pid = "13bd09c9-e403-4432-b3d3-728e31b2d316"

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

    token = client.secrets.get_secret_by_name(secret_name="token", project_id=pid, environment_slug=slug, secret_path="/")
    mongourl = client.secrets.get_secret_by_name(secret_name="mongourl", project_id=pid, environment_slug=slug, secret_path="/")
    errors = client.secrets.get_secret_by_name(secret_name="errors", project_id=pid, environment_slug=slug, secret_path="/")
    openai = client.secrets.get_secret_by_name(secret_name="openai", project_id=pid, environment_slug=slug, secret_path="/")

    os.environ["token"] = token.secretValue
    os.environ["mongourl"] = mongourl.secretValue
    os.environ["errors"] = errors.secretValue
    os.environ["openai"] = openai.secretValue

    if token.secretValue and mongourl.secretValue and errors.secretValue and openai.secretValue:
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

