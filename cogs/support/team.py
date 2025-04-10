import discord
from discord.ext import commands
from discord import app_commands
from internal.universal.premium import isPremium
from internal.universal.staff import staffroleid
import time
import os
import asyncio


class DevCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ### Public Commands ###

    @commands.hybrid_command(name="ping", description="Check bot's latency")
    async def ping(self, ctx):
        start_time = time.time()
        message = await ctx.send("Testing ping...")
        end_time = time.time()

        embed = discord.Embed(
            title="Pong! 🏓",
            description=f"Bot Latency: {round((end_time - start_time) * 1000)}ms\nWebSocket: {round(self.bot.latency * 1000)}ms",
            color=None
        )

        await message.edit(content=None, embed=embed)
        
    @commands.hybrid_command(
        name="help",
        description="Show help"
    )
    async def help(self, ctx):
        await ctx.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="Help",
            description="Hello, I'm Tauri! I'm a bot that helps you with your server. I'm still in development, so please be patient with me!",
            color=None
        )
        embed.add_field(name="Tauri Information", value=f"Servers: `{len(self.bot.guilds)}`\nUsers: `{len(self.bot.users)}`\nLatency: `{round(self.bot.latency * 1000)}ms`")
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url="https://discord.gg/VVBDc3RAqC"))
        view.add_item(discord.ui.Button(label="Documentation", style=discord.ButtonStyle.link, url="https://docs.tauribot.xyz"))
        
        await ctx.send(embed=embed, view=view)
        
        
        
    ## Team Commands ##

    @commands.hybrid_command(
        name="toggle",
        description="Hide or show your support roles."
    )
    @commands.has_role(1359893058447212574) # Make sure this role ID is correct and accessible
    async def toggle_roles(self, ctx):
        """Toggles the visibility of the user's support roles."""
        await ctx.defer(ephemeral=True)
        
        hidden_data = self.bot.db.hiddenroles.find_one({"user_id": ctx.author.id})

        if hidden_data:
            # Roles are currently hidden, let's restore them
            role_ids_to_restore = hidden_data.get("hidden_roles", [])
            roles_to_restore = []
            not_found_roles = []

            for role_id in role_ids_to_restore:
                role = ctx.guild.get_role(role_id)
                if role:
                    roles_to_restore.append(role)
                else:
                    not_found_roles.append(str(role_id)) # Keep track of roles that couldn't be found

            if roles_to_restore:
                try:
                    await ctx.author.add_roles(*roles_to_restore, reason="Toggled roles back on")
                    restored_names = ', '.join([r.name for r in roles_to_restore])
                    message = f"Restored roles: {restored_names}."
                except discord.Forbidden:
                    message = "I don't have permission to add roles back to you."
                except discord.HTTPException as e:
                    message = f"Failed to add roles due to an error: {e}"
            else:
                message = "No valid roles found to restore."

            # Clean up DB entry regardless of success/failure to add roles
            self.bot.db.hiddenroles.delete_one({"user_id": ctx.author.id})

            if not_found_roles:
                message += f"\nNote: Could not find role(s) with ID(s): {', '.join(not_found_roles)}. They might have been deleted."

            await ctx.send(message, ephemeral=True)

        else:
            # Roles are currently visible, let's hide them
            user_roles = ctx.author.roles
            # Ensure staffroleid contains integer IDs
            roles_to_hide = [role for role in user_roles if role.id in staffroleid]

            if roles_to_hide:
                role_ids_to_hide = [role.id for role in roles_to_hide]
                try:
                    await ctx.author.remove_roles(*roles_to_hide, reason="Toggled roles off")
                    removed_names = ', '.join([r.name for r in roles_to_hide])
                    self.bot.db.hiddenroles.update_one(
                        {"user_id": ctx.author.id},
                        {"$set": {"hidden_roles": role_ids_to_hide}},
                        upsert=True
                    )
                    await ctx.send(f"Hid roles: {removed_names}.", ephemeral=True)
                except discord.Forbidden:
                    await ctx.send("I don't have permission to remove roles from you.", ephemeral=True)
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to remove roles due to an error: {e}", ephemeral=True)
            else:
                await ctx.send("You don't have any support roles to hide.", ephemeral=True)
        
    ### Dev Commands ###

    devguild = int(1242439573254963292)

    @commands.hybrid_command(name="sync", description="Sync slash commands")
    @commands.is_owner()
    @app_commands.guilds(discord.Object(id=devguild))  # Dev Guild
    async def sync(self, ctx):
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"Synced {len(synced)} command(s)")
        except Exception as e:
            await ctx.send(f"Failed to sync commands: {e}")

    @commands.hybrid_command(name="reload", description="Reload a cog")
    @app_commands.describe(cog="The cog to reload")
    @commands.is_owner()
    @app_commands.guilds(discord.Object(id=devguild))  # Dev Guild
    async def reload(self, ctx, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"Successfully reloaded cog: {cog}")
        except Exception as e:
            await ctx.send(f"Failed to reload cog: {e}")

async def setup(bot):
    await bot.add_cog(DevCommands(bot))
