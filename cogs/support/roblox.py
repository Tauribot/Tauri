import discord
from discord.ext import commands

import os
import roblox
from roblox import AvatarThumbnailType
import asyncio

async def link_roblox(self, ctx, user_id):
    button = discord.ui.Button(label="Link", style=discord.ButtonStyle.gray, url=f"https://rblx.tauribot.xyz/auth/roblox?discordid={user_id}")
    view = discord.ui.View()
    view.add_item(button)
    await ctx.send(view=view)
    
    attempts = 0
    maxattempt = 60
    
    while attempts < maxattempt:
        try:
            linked_data = self.bot.db.verifications.find_one({"discord": ctx.author.id})
            if linked_data:
                
                client = roblox.Client()
                user = await client.get_user(linked_data["roblox"])
                thumbnail = await client.thumbnails.get_user_avatar_thumbnails(
                    users=[user],
                    type=AvatarThumbnailType.headshot,
                    size=(48, 48)
                )
                
                verified = discord.Embed(
                    title="Account Linked",
                    description=f"Your account {user.name} `{user.id}` has been linked to your Discord account."
                )
                verified.set_thumbnail(url=thumbnail[0].image_url)
                await ctx.send(embed=verified)
                break
            await asyncio.sleep(1)
            attempts += 1
        except Exception as e:
            print(e)
            break
    
    if attempts == maxattempt:
        embed = discord.Embed(
            title="Failed to link account",
            description="Failed to link your account. Please try again later."
        )
        await ctx.send(embed=embed)



class LinkView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
    @discord.ui.button(label="Link a different account", style=discord.ButtonStyle.gray, custom_id="link_different_account")
    async def link_different_account(self, interaction):
        await interaction.defer()
        await link_roblox(self.bot, interaction, interaction.user.id)
            
class Roblox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.hybrid_command(
        name="link",
        description="Link your Roblox account to your Discord account"
    )
    async def link(self, ctx):
        await ctx.defer()
        
        # Check if the user has already linked their Roblox account
        linked_data = self.bot.db.verifications.find_one({"discord": ctx.author.id})
        
        if linked_data:
            embed = discord.Embed(
                title="Roblox Account Already Linked",
                description="You have already linked your Roblox account to your Discord account. By pressing the button below, you can link a different account."
            )
            
            view = LinkView(self.bot)
            
            await ctx.send(embed=embed, view=view)
            
        await link_roblox(self.bot, ctx, ctx.author.id)
        return
        
async def setup(bot):
    await bot.add_cog(Roblox(bot))
            
        
        
        






