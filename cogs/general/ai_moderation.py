import openai
from openai import OpenAI
from discord.ext import commands
import discord
from discord import app_commands
import os
import aiohttp
import asyncio
import typing
import uuid
from internal.universal.premium import isPremium
import json

async def moderation(client, message):
    try:
        response = client.moderations.create(
            input=message,
            model="omni-moderation-latest"
        )
    except Exception as e:
        print(e)
        return
        
    flaggedfor = []
    categories = []
                
        # Check categories and their scores
    categories = response.results[0].categories        
    category_scores = response.results[0].category_scores
    high_threshold = 0.85
    medium_threshold = 0.75
    low_threshold = 0.6

    flaggedfor = []
        
        # Check categories and flag the message if any category is flagged        
    if categories.sexual and category_scores.sexual >= low_threshold:
        flaggedfor.append(f"Sexual: {category_scores.sexual}")

    if categories.sexual_minors and category_scores.sexual_minors >= low_threshold:
        flaggedfor.append(f"Sexual Minors: {category_scores.sexual_minors}")

    if categories.harassment and category_scores.harassment >= high_threshold:
        flaggedfor.append(f"Harassment: {category_scores.harassment}")

    if categories.harassment_threatening and category_scores.harassment_threatening >= medium_threshold:
        flaggedfor.append(f"Harassment Threatening: {category_scores.harassment_threatening}")

    if categories.hate and category_scores.hate >= high_threshold:
        flaggedfor.append(f"Hate: {category_scores.hate}")

    if categories.hate_threatening and category_scores.hate_threatening >= high_threshold:
        flaggedfor.append(f"Hate Threatening: {category_scores.hate_threatening}")

    if categories.illicit and category_scores.illicit >= medium_threshold:
        flaggedfor.append(f"Illicit: {category_scores.illicit}")

    if categories.illicit_violent and category_scores.illicit_violent >= medium_threshold:
        flaggedfor.append(f"Illicit Violent: {category_scores.illicit_violent}")

    if categories.self_harm and category_scores.self_harm >= low_threshold:
        flaggedfor.append(f"Self Harm: {category_scores.self_harm}")

    if categories.self_harm_intent and category_scores.self_harm_intent >= low_threshold:
        flaggedfor.append(f"Self Harm Intent: {category_scores.self_harm_intent}")

    if categories.self_harm_instructions and category_scores.self_harm_instructions >= low_threshold:
        flaggedfor.append(f"Self Harm Instructions: {category_scores.self_harm_instructions}")

    if categories.violence and category_scores.violence >= medium_threshold:
        flaggedfor.append(f"Violence: {category_scores.violence}")

    if categories.violence_graphic and category_scores.violence_graphic >= medium_threshold:
        flaggedfor.append(f"Violence Graphic: {category_scores.violence_graphic}")
    
    return flaggedfor

class aimod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai = os.getenv("openai")
        self.client = OpenAI(api_key=self.openai)
        self.model = "gpt-4o-mini-search-preview"
        if not self.openai:
            print("OpenAI API key not found in environment variables!")
                
    @commands.hybrid_command(
        name="moderation",
        description="Check if a message is flagged for moderation."
    )
    async def moderation(self, ctx, *, message: str):
        """Check if a message is flagged for moderation."""
        await ctx.defer()
        
        flaggedFor = await moderation(self.client, message)
                    
        if flaggedFor:
            readable = ', '.join(flaggedFor)  # Join flagged items into a readable string
            print("Attempting to delete the message...")
            try:
                await ctx.message.delete()
                print("Message deleted successfully.")
            except discord.Forbidden:
                print("Bot does not have permission to delete messages.")
            except discord.HTTPException as e:
                print(f"Failed to delete message: {e}")

            embed = discord.Embed(
                title="Message Flagged | AI Moderation",
                description=f"{readable}",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Message not flagged for moderation.")
            
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild.id != 1242439573254963292:
            return
                
        if message.content:
            results = await moderation(self.client, message.content)            
            if results:
                await message.delete()
                beautify = ', '.join(results)                
                embed = discord.Embed(
                    title="Message Flagged",
                    description=f"Your message was flagged for moderation. Please rephrase your message and try again.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text=f"AI Moderation")
                msg = await message.channel.send(embed=embed)
                await msg.delete(delay=3)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        
        await self.on_message(after)
            
                     

async def setup(bot):
    await bot.add_cog(aimod(bot))

