import discord
from discord.ext import commands
from discord import app_commands
import ffmpeg

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(
        name="voice",
        description="Voice channel commands"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def voice(self, ctx):
        pass

    @voice.command(
        name="join",
        description="Join a voice channel"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def join(self, ctx):
        """Join the voice channel"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f"Joined {channel.name}")
        else:
            await ctx.send("You are not in a voice channel.")

    @voice.command(
        name="leave",
        description="Leave the voice channel"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def leave(self, ctx):
        """Leave the voice channel"""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected from the voice channel.")
        else:
            await ctx.send("I am not in a voice channel.")

    @voice.command(
        name="play",
        description="Play audio in the voice channel"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def play(self, ctx):
        """Play audio in the voice channel"""
        if ctx.voice_client:
            source = discord.FFmpegPCMAudio('voice/start.mp3')
            ctx.voice_client.play(source)
            await ctx.send("Now playing: voice/start.mp3")
        else:
            await ctx.send("I am not in a voice channel.")

async def setup(bot):
    await bot.add_cog(Voice(bot))
