from fastapi import FastAPI, Response, status, Request
import uvicorn
from discord.ext import commands
import aiohttp
import asyncio
import pymongo
import os
from pymongo.errors import ConnectionFailure
from fastapi.responses import RedirectResponse
from linked_roles import LinkedRolesOAuth2, RoleConnection
from internal.universal.staff import has_role

client = LinkedRolesOAuth2(
    client_id='1349452382924443819',
    client_secret='2-zS_ejdJCvVH82OKtG48deHqNM9sCFx',
    redirect_uri='https://staff.tauribot.xyz/verified-role',
    scopes=('role_connections.write', 'identify'),
)

app = FastAPI(
    title="Bot API",
    description="API endpoints for the Discord bot",
    version="1.0.0"
)

async def start_api():
    """Start the FastAPI server"""
    config = uvicorn.Config(app, host="0.0.0.0", port=8888, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
    await client.start()
    return True

class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = app  # Ensure you have the FastAPI instance
        self.api_task = asyncio.create_task(start_api())
        self.app.state.bot = bot
        
    @app.get('/linked-role')
    async def linked_roles(self):
        url = client.get_oauth_url()
        return RedirectResponse(url=url)

    @app.get('/verified-role')
    async def verified_role(self, code: str):
        token = await client.get_access_token(code)
        user = await client.fetch_user(token)
        if user is None:
            raise Exception('User not found')
        
        # Check if the user has staff roles
        roles = await has_role(self.bot, user)  

        role = await user.fetch_role_connection()
        if role is None:
            role = RoleConnection(platform_name='Discord', platform_username=str(user))
            role.add_metadata(key='is_staff', value=bool(roles))
            await user.edit_role_connection(role)
        
        return 'Role metadata set successfully. Please check your Discord profile.'

async def setup(bot):
    await bot.add_cog(API(bot))