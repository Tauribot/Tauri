import discord
from discord.ext import commands

import os
import roblox
from roblox import AvatarThumbnailType
import asyncio

class ConfirmLinkView(discord.ui.View):
    def __init__(self, bot, ctx, user_id, is_relink=False):
        super().__init__()
        self.bot = bot
        self.ctx = ctx
        self.user_id = user_id
        self.is_relink = is_relink
        self.message = None
        
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # If relinking, remove the old account first
        if self.is_relink:
            discord_id = int(self.ctx.author.id)
            self.bot.db.verifications.delete_one({"discord": discord_id})
            
        # Update embed to show linking in progress
        embed = discord.Embed(
            title="Linking in Progress",
            description="Please click the link below and follow the instructions to link your Roblox account."
        )
        
        # Create link button
        link_button = discord.ui.Button(label="Link", style=discord.ButtonStyle.gray, 
                                        url=f"https://rblx.tauribot.xyz/auth/roblox?discordid={self.user_id}")
        link_view = discord.ui.View()
        link_view.add_item(link_button)
        
        # Edit the message
        await self.message.edit(embed=embed, view=link_view)
        
        # Wait for verification
        attempts = 0
        maxattempt = 60
        
        while attempts < maxattempt:
            try:
                # Force integer ID for consistent database lookup
                discord_id = int(self.ctx.author.id)
                linked_data = self.bot.db.verifications.find_one({"discord": discord_id})
                
                # Debug print to check if it finds anything
                print(f"Checking for discord ID: {discord_id}, Found: {linked_data is not None}")
                
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
                    await self.message.edit(embed=verified, view=None)
                    self.stop()  # Stop the view once linked
                    break
                await asyncio.sleep(1)
                attempts += 1
            except Exception as e:
                print(e)
                error_embed = discord.Embed(
                    title="Error",
                    description=f"An error occurred: {str(e)}"
                )
                await self.message.edit(embed=error_embed, view=None)
                break
        
        if attempts == maxattempt:
            embed = discord.Embed(
                title="Failed to link account",
                description="Failed to link your account. Please try again later."
            )
            await self.message.edit(embed=embed, view=None)
            
    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # If canceling a relink
        if self.is_relink:
            embed = discord.Embed(
                title="Relink Cancelled",
                description="Your existing Roblox account link has been kept."
            )
        else:
            embed = discord.Embed(
                title="Link Cancelled",
                description="You've chosen not to link a Roblox account."
            )
            
        await self.message.edit(embed=embed, view=None)
        self.stop()

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
        discord_id = int(ctx.author.id)
        linked_data = self.bot.db.verifications.find_one({"discord": discord_id})
        
        if linked_data:
            # User already has a linked account
            client = roblox.Client()
            user = await client.get_user(linked_data["roblox"])
            
            embed = discord.Embed(
                title="Roblox Account Already Linked",
                description=f"You already have a Roblox account linked: {user.name} `{user.id}`\nDo you want to link a different account instead?"
            )
            
            view = ConfirmLinkView(self.bot, ctx, ctx.author.id, is_relink=True)
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg
            
        else:
            # User has no linked account
            embed = discord.Embed(
                title="Link Roblox Account",
                description="Would you like to link your Roblox account to your Discord account?"
            )
            
            view = ConfirmLinkView(self.bot, ctx, ctx.author.id)
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg
        
async def setup(bot):
    await bot.add_cog(Roblox(bot))