from fastapi import FastAPI, Response, status, Request, HTTPException
import uvicorn
from discord.ext import commands
import aiohttp
import asyncio
import pymongo
import os
from pymongo.errors import ConnectionFailure
from fastapi.responses import RedirectResponse
from linked_roles import LinkedRolesOAuth2, RoleConnection, RoleMetadataType, RoleMetadataRecord
from internal.universal.staff import has_role

# Initialize LinkedRolesOAuth2 client
client = LinkedRolesOAuth2(
    client_id=os.getenv("client_id"),
    client_secret=os.getenv("client_secret"),
    redirect_uri='https://staff.tauribot.xyz/verified-role', # Ensure this matches Discord Dev Portal
    token=os.getenv("token"),
    scopes=('role_connections.write', 'identify'),
)

# Initialize FastAPI app
app = FastAPI(
    title="Bot API",
    description="API endpoints for the Discord bot",
    version="1.0.0"
)

# --- FastAPI Route Definitions ---

@app.get('/linked-role')
async def linked_roles():
    """Redirects users to Discord OAuth2 authorization page."""
    url = client.get_oauth_url()
    return RedirectResponse(url=url)

@app.get('/verified-role')
async def verified_role(request: Request, code: str):
    """
    Handles the OAuth2 callback, fetches user info, checks roles,
    and updates Discord role connection metadata.
    """
    try:
        token = await client.get_access_token(code)
        user = await client.fetch_user(token)
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching token or user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process OAuth callback")

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found after OAuth")

    # Access bot instance from app state
    bot = request.app.state.bot
    if not bot:
         # Log this critical error
         print("Error: Bot instance not found in app state!")
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server configuration error")

    # Check if the user has staff roles using the bot instance
    try:
        is_staff_member = await has_role(bot, user)
    except Exception as e:
        # Log error during role check
        print(f"Error checking user roles for {user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check user roles")

    # Fetch or create role connection object
    try:
        role_connection = await user.fetch_role_connection()
        if role_connection is None:
            role_connection = RoleConnection(platform_name='Tauri Staff', platform_username=str(user)) # Customize platform_name if desired

        # Update metadata based on roles check
        # Ensure the key 'is_staff' matches the one registered
        role_connection.add_metadata(key='is_staff', value=1 if is_staff_member else 0) # Use 1/0 for boolean

        await user.edit_role_connection(role_connection)
    except Exception as e:
        # Log error during role connection update
        print(f"Error updating role connection for {user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update Discord role connection")

    return 'Role metadata set successfully. Please check your Discord profile.'

# --- API Server Management ---

async def start_api(bot_instance):
    """Starts the FastAPI server with the bot instance in state."""
    app.state.bot = bot_instance # Store bot instance in app state
    config = uvicorn.Config(app, host="0.0.0.0", port=8888, log_level="info")
    server = uvicorn.Server(config)
    # Consider running client.start() if it's necessary and non-blocking,
    # or manage its lifecycle elsewhere if it's a long-running task.
    # await client.start()
    print("Starting FastAPI server...")
    await server.serve()
    print("FastAPI server stopped.")
    return True

# --- Discord Cog Definition ---

class API(commands.Cog):
    """Cog to manage the FastAPI server and related bot commands."""
    def __init__(self, bot):
        self.bot = bot
        self.api_task = None
        # Start the API server in the background when the cog loads
        self.api_task = asyncio.create_task(start_api(self.bot))
        print("API Cog initialized, starting FastAPI server task.")

    async def cog_unload(self):
        """Clean up the API task when the cog is unloaded."""
        if self.api_task and not self.api_task.done():
            self.api_task.cancel()
            print("FastAPI server task cancelled.")

    @commands.hybrid_command(
        name='setup-linked-role',
        description='Setup the linked role metadata for the bot',
        aliases=['slr']
    )
    @commands.is_owner()
    async def setup_linked_role(self, ctx: commands.Context):
        """Command to register the necessary role connection metadata with Discord."""
        await ctx.defer(ephemeral=True)
        records = [
            RoleMetadataRecord(
                key='is_staff', # Must match the key used in the /verified-role endpoint
                name='Tauri Staff Member', # User-facing name
                description='Whether the user is a verified staff member.', # User-facing description
                type=RoleMetadataType.boolean_equal, # Use boolean type
            )
        ]

        try:
            registered_records = await client.register_role_metadata(records=records, force=True)
            await ctx.send(f'Registered role metadata successfully: {registered_records}', ephemeral=True)
            print(f"Role metadata registered: {registered_records}")
        except Exception as e:
            await ctx.send(f'Failed to register role metadata: {e}', ephemeral=True)
            print(f"Error registering role metadata: {e}")

# --- Cog Setup Function ---

async def setup(bot):
    """Adds the API cog to the bot."""
    await bot.add_cog(API(bot))
    print("API Cog added to bot.")