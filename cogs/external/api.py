from fastapi import FastAPI, Response, status, Request
import time
import uvicorn
from typing import Dict
from discord.ext import commands
import aiohttp
import asyncio
import pymongo
import os
from pymongo.errors import ConnectionFailure

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

@app.get("/api/db-health")
async def db_health_check():
    cluster = pymongo.MongoClient(os.getenv("mongourl"))
    try:
        # Perform a simple operation to check DB health
        cluster.admin.command("ping")
        return Response(
            content='{"status": "healthy", "db": "connected"}',
            media_type="application/json",
            status_code=status.HTTP_200_OK
        )
    except ConnectionFailure:
        return Response(
            content='{"status": "unhealthy", "db": "disconnected"}',
            media_type="application/json",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = app
        self.api_task = asyncio.create_task(start_api())
        self.app.state.bot = bot

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
