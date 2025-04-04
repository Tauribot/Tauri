import discord
from discord.ext import commands
import os
import datetime
import ffmpeg
from discord.utils import get
# import pynacl
import assemblyai as aai

async def on_record_error(e):
    print(f"Recording error: {e}")


class VoiceRecorder(commands.Cog):
    def __init__(self, bot):
        self.sink = None
        self.bot = bot
        self.voice_clients = {}  # Store voice clients per guild
        self.recording_states = {}  # Store recording states per guild
        self.filenames = {} # Store filenames per guild

    def get_voice_client(self, guild_id):
        return self.voice_clients.get(guild_id)

    def set_voice_client(self, guild_id, voice_client):
        self.voice_clients[guild_id] = voice_client

    def clear_voice_client(self, guild_id):
        if guild_id in self.voice_clients:
            del self.voice_clients[guild_id]

    def is_recording(self, guild_id):
        return self.recording_states.get(guild_id, False)

    def set_recording_state(self, guild_id, state):
        self.recording_states[guild_id] = state
    
    def set_filename(self, guild_id, filename):
        self.filenames[guild_id] = filename
    
    def get_filename(self, guild_id):
        return self.filenames.get(guild_id)

    @commands.hybrid_group(
        name="recorder",
        description="Voice recorder commands"
    )
    async def recorder(self, ctx):
        """Base command for voice recorder."""
        pass

    @recorder.command(
        name="start",
        description="Start recording in the voice channel."
    )
    async def start_recording(self, ctx):
        guild_id = ctx.guild.id
        voice_client = self.get_voice_client(guild_id)

        if voice_client is not None and voice_client.is_connected():
            await ctx.send("Already connected to a voice channel in this server.")
            return
        
        # Add logging here
        print(f"ctx.author.voice: {ctx.author.voice}")
        if ctx.author.voice:
            print(f"ctx.author.voice.channel: {ctx.author.voice.channel}")
        
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("You are not connected to a voice channel.")
            return

        channel = ctx.author.voice.channel
        try:
            voice_client = await channel.connect()
            self.set_voice_client(guild_id, voice_client)
        except discord.errors.ClientException:
            await ctx.send("Already connected to this voice channel.")
            return
        except discord.errors.Forbidden:
            await ctx.send("Failed to connect to the voice channel. Check permissions.")
            return

        # Play start audio
        source = discord.FFmpegPCMAudio(os.path.join('voice', 'start.mp3'))
        try:
            voice_client.play(source, after=lambda e: print('Start audio finished', e))
        except discord.errors.ClientException as e:
            await ctx.send(f"FFmpeg was not found. Please install FFmpeg and ensure it's in your system's PATH. Error: {e}")
            return

        # Generate unique filename
        filename = f"recording_{guild_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        self.set_filename(guild_id, filename)
        
        # Create sink with correct import
        self.sink = discord.sinks.WaveSink()
        
        # Start recording with correct parameters
        voice_client.start_recording(
            self.sink,
            self.after_record,
            self.on_record_error
        )
        self.set_recording_state(guild_id, True)  # Set the recording flag to True
        await ctx.send("Started recording.")

    @recorder.command(
        name="stop",
        description="Stop recording in the voice channel."
    )
    async def stop_recording(self, ctx):
        guild_id = ctx.guild.id
        if not self.is_recording(guild_id):  # Check if recording is active
            await ctx.send("Not currently recording in this server.")
            return

        voice_client = self.get_voice_client(guild_id)
        if voice_client and voice_client.is_connected():
            voice_client.stop_recording()
            self.set_recording_state(guild_id, False)  # Set the recording flag to False
            await ctx.send("Stopped recording.")
        else:
            await ctx.send("Not currently connected to a voice channel in this server.")

    async def on_voice_state_update(self, member, before, after):
        guild_id = member.guild.id
        voice_client = self.get_voice_client(guild_id)

        if voice_client is None:
            return

        if member == self.bot.user:
            return

        # Add logging here
        print(f"Voice state update for {member.name}:")
        print(f"Before: {before}")
        print(f"After: {after}")

        if voice_client.channel is None:
            return

        if len(voice_client.channel.members) == 1:
            # Only the bot is in the channel, stop recording
            await self.stop_recording_from_event(guild_id)

    async def stop_recording_from_event(self, guild_id):
        if not self.is_recording(guild_id):  # Check if recording is active
            return

        voice_client = self.get_voice_client(guild_id)
        if voice_client and voice_client.is_connected():
            voice_client.stop_recording()
            self.set_recording_state(guild_id, False)  # Set the recording flag to False
            print("Stopped recording due to empty channel.")
            self.clear_voice_client(guild_id)
        else:
            print("No voice client found for this server.")
            self.clear_voice_client(guild_id)

    async def on_record_error(self, sink, error):
        print(f"Recording error: {error}")

    async def after_record(self, sink, exception=None):
        # Get guild_id from sink
        guild_id = None
        for client in self.voice_clients.items():
            if client[1].recording:
                guild_id = client[0]
                break
                
        if guild_id is None:
            print("Could not determine guild_id for finished recording")
            return
            
        # Save to file
        filename = self.get_filename(guild_id)
        if not filename:
            print("Filename not found for this server.")
            return
        
        for user_id, audio in sink.audio_data.items():
            try:
                user = await self.bot.fetch_user(user_id)
                if user:
                    file_friendly_name = filename.replace(".wav", f"_{user.name}.wav")
                    with open(file_friendly_name, "wb") as f:
                        f.write(audio.file.read())
                else:
                    print(f"Could not fetch user {user_id}")
            except Exception as e:
                print(f"Error saving audio for user {user_id}: {e}")
        
        self.sink = None
        self.clear_voice_client(guild_id)


async def setup(bot):
    await bot.add_cog(VoiceRecorder(bot))

