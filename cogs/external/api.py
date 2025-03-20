from fastapi import FastAPI, Response, status
import time
import uvicorn
from typing import Dict
from discord.ext import commands
import aiohttp
import asyncio

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
    return True

@app.get("/api/health")
async def health_check():
    return { "status": "healthy" }

class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = app
        self.api_task = asyncio.create_task(start_api())

    async def cog_unload(self):
        """Stop API when cog is unloaded"""
        if hasattr(self, 'api_task'):
            self.api_task.cancel()

    @commands.command(
        name="api",
        description="Get the API URL"
    )
    @commands.is_owner()
    async def api(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8888/api/health") as resp:
                data = await resp.json()
                await ctx.send(f"API Status: {data.get('status')}")

async def setup(bot):
    await bot.add_cog(API(bot))