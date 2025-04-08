import discord
import asyncio
import pymongo
from dotenv import load_dotenv
from discord.ext import commands
import pymongo.database
import sentry_sdk
from sentry_sdk.integrations.pymongo import PyMongoIntegration
import os
from infisical_sdk import InfisicalSDKClient

load_dotenv()
if os.getenv("environment") == "development":
    bot = commands.Bot(command_prefix=commands.when_mentioned_or('>'), intents=discord.Intents.all())
elif os.getenv("environment") == "production":
    bot = commands.Bot(command_prefix=commands.when_mentioned_or('-'), intents=discord.Intents.all())
elif os.getenv("environment") == None:
    raise Exception("Work environment not set.")

async def setup_database():
    """Initialize database connection"""
    bot.cluster = pymongo.MongoClient(os.getenv("mongourl"))
    if os.getenv("environment") == "development":
        bot.db = pymongo.database.Database(bot.cluster, "cognition-dev")
    elif os.getenv("environment") == "production":
        bot.db = pymongo.database.Database(bot.cluster, "cognition")
    
    await asyncio.sleep(1)
    
    if bot.cluster:
        print("Connected to the database")
        return True
    else:
        raise Exception("Failed to connect to database")

@bot.event 
async def on_ready():
    await bot.change_presence(status=discord.Status.idle)
    channel = bot.get_channel(1349463744278691870)
    await channel.send(f"{bot.user.name} is ready to serve!")
    print(f"Logged in as {bot.user}")

@bot.before_invoke
async def before_invoke(ctx):
    search = bot.db.blocklist.find_one({"user_id": ctx.author.id})
    if search:
        if search["user_id"] == ctx.author.id:
            support_url = os.getenv("support_url")
            blockedembed = discord.Embed(
                title="Service Access Revoked",
                description=f"You are not eligible to use our service due to a violation of our Terms of Service. If you believe this is a mistake, please contact support.",
                colour=None
            )
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="Support", url=support_url))

            await ctx.reply(embed=blockedembed, view=view, ephemeral=True)
            raise commands.DisabledCommand()
    pass

@bot.after_invoke
async def after_invoke(ctx):
    bot.db.commands.insert_one({
        "username": ctx.author.name,
        "userid": ctx.author.id,
        "command": ctx.command.qualified_name,
        "guild": ctx.guild.id if ctx.guild else None,
        "channel": ctx.channel.id
    })
    pass
            
async def secrets():
    client = InfisicalSDKClient(host="https://app.infisical.com")

    pid = "1fc23486-c8b2-4135-a02a-a40be32b3d65"

    if os.getenv("environment") == "production":
        slug = "prod"
    else:
        slug = "dev"

    if os.getenv("vaultid") is None or os.getenv("vaultsecret") is None:
        raise Exception("Vault ID or Secret not set.")

    client.auth.universal_auth.login(
        client_id=os.getenv("vaultid"), 
        client_secret=os.getenv("vaultsecret")
    )

    listall = client.secrets.list_secrets(project_id=pid, environment_slug=slug, secret_path="/")

    preos = []
    completed = []

    for secret in listall.secrets:
        preos.append(secret.secretKey)

    for secret in preos:
        request = client.secrets.get_secret_by_name(secret_name=secret, project_id=pid, environment_slug=slug, secret_path="/")
        os.environ[secret] = request.secretValue
        completed.append(secret)

    if len(completed) == len(preos):
        print(f"Secrets Available [{len(completed)}]: " + str(completed))
        completed = []
        preos = []
        return True
    else:
        raise Exception("Failed to load secrets")

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
            dsn="https://20c9af3eab9646c5b6f2d1cb4598e5dd@o4508966144376832.ingest.us.sentry.io/4508966147522560",
            traces_sample_rate=1.0,
            integrations=[PyMongoIntegration()],
            profiles_sample_rate=1.0
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
        try:
            await bot.start(token)
        except Exception as e:
            print(f"Error starting bot: {str(e)}")
            return

asyncio.run(main())
