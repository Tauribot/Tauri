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
from linked_roles import LinkedRolesOAuth2, OAuth2Scopes
from internal.universal.staff import has_role
from internal.universal.premium import isPremium

# Initialize OAuth2 client
client = LinkedRolesOAuth2(
    client_id=os.getenv("client_id"),
    client_secret=os.getenv("client_secret"),
    redirect_uri='https://admin.tauribot.xyz/callback',
    token=os.getenv("token"),
    scopes=(OAuth2Scopes.identify, OAuth2Scopes.guilds),
)

# Initialize FastAPI app
app = FastAPI(
    title="Bot Admin Panel",
    description="Admin panel for the Discord bot",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Admin routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

@app.get("/login")
async def login():
    url = client.get_oauth_url()
    return RedirectResponse(url=url)

@app.get("/callback")
async def callback(request: Request, code: str):
    try:
        token = await client.get_access_token(code)
        user = await client.fetch_user(token)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process OAuth callback")

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is admin
    bot = request.app.state.bot
    if not bot:
        raise HTTPException(status_code=500, detail="Internal server configuration error")

    is_admin = await has_role(bot, user)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Store user session
    request.session["user"] = {
        "id": user.id,
        "username": user.name,
        "avatar": user.avatar.url if user.avatar else None
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