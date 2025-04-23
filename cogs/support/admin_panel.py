from fastapi import FastAPI, Response, status, Request, HTTPException, Depends, Form
import uvicorn
from discord.ext import commands
import aiohttp
import json
import asyncio
import pymongo
import os
from pymongo.errors import ConnectionFailure
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from internal.universal.staff import has_role
from internal.universal.premium import isPremium
import urllib.parse

# Initialize FastAPI app
app = FastAPI(
    title="Bot Admin Panel",
    description="Admin panel for the Discord bot",
    version="1.0.0"
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("session_secret", "209ej2309jsdf0c9j0923k9r09wekj09sdikf")
)

# Mount static files
app.mount("/static", StaticFiles(directory="./app/internal/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="./app/templates")

# OAuth2 configuration
DISCORD_CLIENT_ID = os.getenv("client_id")
DISCORD_CLIENT_SECRET = os.getenv("client_secret")
DISCORD_REDIRECT_URI = "https://admin.tauribot.xyz/callback"
DISCORD_API_ENDPOINT = "https://discord.com/api/v10"
DISCORD_TOKEN_URL = f"{DISCORD_API_ENDPOINT}/oauth2/token"
DISCORD_USER_URL = f"{DISCORD_API_ENDPOINT}/users/@me"

# Admin routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

@app.get("/login")
async def login():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds"
    }
    url = f"{DISCORD_API_ENDPOINT}/oauth2/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url)

@app.get("/callback")
async def callback(request: Request, code: str):
    try:
        # Exchange code for token
        data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_TOKEN_URL, data=data, headers=headers) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=400, detail="Failed to get access token")
                token_data = await resp.json()
                
            # Get user info
            headers = {
                "Authorization": f"Bearer {token_data['access_token']}"
            }
            async with session.get(DISCORD_USER_URL, headers=headers) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=400, detail="Failed to get user info")
                user_data = await resp.json()
                
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process OAuth callback")

    # Check if user is admin
    bot = request.app.state.bot
    if not bot:
        raise HTTPException(status_code=500, detail="Internal server configuration error")

    is_admin = await has_role(bot, user_data)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Store user session
    request.session["user"] = {
        "id": user_data["id"],
        "username": user_data["username"],
        "avatar": f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png" if user_data.get("avatar") else None
    }

    return RedirectResponse(url="/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user
    })

# User Management Routes
@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/")
    
    bot = request.app.state.bot
    if not bot:
        raise HTTPException(status_code=500, detail="Internal server configuration error")

    # Get blocked users
    blocked_users = list(bot.db.blocklist.find())
    blocked_users = [{"user_id": user["user_id"]} for user in blocked_users]

    # Get premium users
    premium_users = list(bot.db.premium.find())
    premium_users = [{"user_id": user["user_id"]} for user in premium_users]

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": user,
        "blocked_users": blocked_users,
        "premium_users": premium_users
    })

@app.post("/users/block")
async def block_user(request: Request, user_id: str = Form(...)):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    bot = request.app.state.bot
    if not bot:
        raise HTTPException(status_code=500, detail="Internal server configuration error")

    try:
        bot.db.blocklist.insert_one({"user_id": int(user_id)})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/users/unblock")
async def unblock_user(request: Request, user_id: str = Form(...)):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    bot = request.app.state.bot
    if not bot:
        raise HTTPException(status_code=500, detail="Internal server configuration error")

    try:
        bot.db.blocklist.delete_one({"user_id": int(user_id)})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/users/premium")
async def add_premium(request: Request, user_id: str = Form(...)):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    bot = request.app.state.bot
    if not bot:
        raise HTTPException(status_code=500, detail="Internal server configuration error")

    try:
        bot.db.premium.insert_one({"user_id": int(user_id)})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/users/premium/remove")
async def remove_premium(request: Request, user_id: str = Form(...)):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    bot = request.app.state.bot
    if not bot:
        raise HTTPException(status_code=500, detail="Internal server configuration error")

    try:
        bot.db.premium.delete_one({"user_id": int(user_id)})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

class AdminPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = app
        self.app.state.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Start the FastAPI server
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

async def setup(bot):
    if os.getenv("env") == "development":
        raise commands.CommandError("Admin panel is not available in development mode")
    await bot.add_cog(AdminPanel(bot))  