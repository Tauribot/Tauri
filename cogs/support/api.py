from fastapi import FastAPI, Response, status, Request, HTTPException
import uvicorn
from discord.ext import commands
import aiohttp
import json
import asyncio
import pymongo
import os
from pymongo.errors import ConnectionFailure
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager # Import asynccontextmanager
from linked_roles import LinkedRolesOAuth2, OAuth2Scopes
from linked_roles import RoleConnection, RoleMetadataRecord, RoleMetadataType
from internal.universal.staff import has_role

# Initialize LinkedRolesOAuth2 client
client = LinkedRolesOAuth2(
    client_id=os.getenv("client_id"),
    client_secret=os.getenv("client_secret"),
    redirect_uri='https://staff.tauribot.xyz/verified-role', # Ensure this matches Discord Dev Portal
    token=os.getenv("token"),
    scopes=(OAuth2Scopes.role_connection_write, OAuth2Scopes.identify),
)

# --- FastAPI Lifespan Management ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    await client.start() # Start the client's internal session
    yield
    # Code to run on shutdown
    print("FastAPI shutdown: Closing linked_roles client...")


# Initialize FastAPI app with lifespan manager
app = FastAPI(
    title="Bot API",
    description="API endpoints for the Discord bot",
    version="1.0.0",
    lifespan=lifespan # Register the lifespan context manager
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
        # The client should be ready now due to the lifespan event
        token = await client.get_access_token(code)
        user = await client.fetch_user(token)
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching token or user: {e}") # Keep this log
        # Consider more specific error handling if possible
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process OAuth callback")

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found after OAuth")

    # Access bot instance from app state
    bot = request.app.state.bot
    if not bot:
         print("Error: Bot instance not found in app state!")
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server configuration error")

    # Check if the user has staff roles using the bot instance
    try:
        is_staff_member = await has_role(bot, user)
    except Exception as e:
        print(f"Error checking user roles for {user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check user roles")

    # Fetch or create role connection object
    try:
        role_connection = await user.fetch_role_connection()
        if role_connection is None:
            role_connection = RoleConnection(platform_name='Tauri Staff', platform_username=str(user))
            role_connection.add_metadata(key='is_staff', value=True if is_staff_member else False)

        if role_connection.metadata.get('is_staff') != is_staff_member:
            role_connection.metadata['is_staff'] = is_staff_member
            print(f"Updated role connection metadata for {user.id}: {role_connection.metadata}")
        else:
            print(f"Role connection metadata for {user.id} is already up to date.")

        await user.edit_role_connection(role_connection)
    except Exception as e:
        print(f"Error updating role connection for {user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update Discord role connection")

    return 'Role metadata set successfully. Please check your Discord profile.'

# --- API Server Management ---

async def start_api(bot_instance):
    """Starts the FastAPI server with the bot instance in state."""
    # Store bot instance BEFORE server starts, accessible in lifespan
    app.state.bot = bot_instance
    config = uvicorn.Config(app, host="0.0.0.0", port=8888, log_level="info")
    server = uvicorn.Server(config)
    # client.start() is now handled by the lifespan manager
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

    async def cog_unload(self):
        """Clean up the API task when the cog is unloaded."""
        if self.api_task and not self.api_task.done():
            self.api_task.cancel()
            try:
                await self.api_task # Allow task to finish cancellation
            except asyncio.CancelledError:
                print("FastAPI server task cancelled successfully.")
            except Exception as e:
                print(f"Error during API task cancellation: {e}")
        else:
            print("API task already completed or not running.")

    @commands.hybrid_command(
        name='setup-linked-role',
        description='Setup the linked role metadata for the bot',
        aliases=['slr']
    )
    @commands.is_owner()
    async def setup_linked_role(self, ctx: commands.Context):
        """Command to register the necessary role connection metadata with Discord via HTTP."""
        await ctx.defer(ephemeral=True)

        client_id = os.getenv("client_id")
        bot_token = os.getenv("token")

        if not client_id or not bot_token:
            await ctx.send("Error: `client_id` or `token` environment variable not set.", ephemeral=True)
            print("Error: Missing client_id or token for role metadata registration.")
            return

        url = f'https://discord.com/api/v10/applications/{client_id}/role-connections/metadata'

        # Define the metadata payload
        body = [
            {
                'key': 'is_staff', # Your specific key
                'name': 'Tauri Staff Member', # User-facing name
                'description': 'Whether the user is a verified staff member.', # User-facing description
                'type': 7, # 7 corresponds to boolean_equal
            }
        ]

        headers = {
          'Content-Type': 'application/json',
          'Authorization': f'Bot {bot_token}',
        }

        try:
            # Create a temporary session for this request
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.put(url, data=json.dumps(body)) as response:
                    if response.ok:
                        try:
                            data = await response.json()
                            await ctx.send(f'Registered role metadata successfully: ```json\n{json.dumps(data, indent=2)}```', ephemeral=True)
                            print(f"Role metadata registered: {data}")
                        except aiohttp.ContentTypeError:
                            # Handle cases where response is OK but not JSON (shouldn't happen for this endpoint on success)
                            text_data = await response.text()
                            await ctx.send(f'Registered role metadata successfully (non-JSON response): ```\n{text_data}```', ephemeral=True)
                            print(f"Role metadata registered (non-JSON): {text_data}")
                    else:
                        # Handle error response
                        error_text = await response.text()
                        await ctx.send(f'Failed to register role metadata. Status: {response.status}\n```\n{error_text}```', ephemeral=True)
                        print(f"Error registering role metadata. Status: {response.status}, Response: {error_text}")

        except aiohttp.ClientError as e:
            # Handle client-side errors (e.g., connection refused)
            await ctx.send(f'Failed to register role metadata due to a connection error: {e}', ephemeral=True)
            print(f"aiohttp ClientError during role metadata registration: {e}")
        except Exception as e:
            # Handle other unexpected errors
            await ctx.send(f'An unexpected error occurred: {e}', ephemeral=True)
            print(f"Unexpected error during role metadata registration: {e}")
# --- Cog Setup Function ---

async def setup(bot):
    """Adds the API cog to the bot."""
    await bot.add_cog(API(bot))
    print("API Cog added to bot.")