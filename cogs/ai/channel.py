from openai import OpenAI
from discord.ext import commands
import discord
import os
import logging
import time
import asyncio

class aichannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.apikey = os.getenv("openai")
        self.client = OpenAI(api_key=self.apikey)  # Create client once
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("AI Channel cog initialized")
        if not self.apikey:
            self.logger.error("OpenAI API key not found in environment variables!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if message.channel.id == 1350667412130762812:
            
            async with message.channel.typing():  # Show typing indicator
                try:
                    channel = self.bot.get_channel(1350667412130762812)
                    if not channel:
                        return
                    
                    # Reduce history size and process concurrently
                    history = []
                    async for msg in channel.history(limit=5):  # Reduced from 10 to 5
                        history.append(msg)
                    
                    filteredcontext = [msg.content for msg in history if msg.author.id != message.author.id]
                    
                    response = await asyncio.to_thread(
                        self.client.chat.completions.create,
                        model="o3-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": "\n".join(filteredcontext) + "\n" + message.content},
                        ],
                    )
                    
                    await message.reply(response.choices[0].message.content)
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    await message.reply("Sorry, there was an error processing your message.")

async def setup(bot):
    await bot.add_cog(aichannel(bot))