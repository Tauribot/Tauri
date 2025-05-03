import discord
from discord.ext import commands
from discord import app_commands

tauriServerId = 1242439573254963292

class RoleToggleButton(discord.ui.Button):
    def __init__(self, role: discord.Role):
        super().__init__(label=role.name, style=discord.ButtonStyle.secondary)
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        if self.role in member.roles:
            await member.remove_roles(self.role)
            await interaction.response.send_message(
                f"Removed role {self.role.name} successfully", ephemeral=True
            )
        else:
            await member.add_roles(self.role)
            await interaction.response.send_message(
                f"Added role {self.role.name} successfully", ephemeral=True
            )

class RoleToggleView(discord.ui.View):
    def __init__(self, roles: list[discord.Role]):
        super().__init__(timeout=None)
        for role in roles:
            self.add_item(RoleToggleButton(role))

class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(
        name="utilities",
        description="Utilities for the Tauri Discord server."
    )
    @app_commands.guilds(discord.Object(id=tauriServerId))
    @commands.has_guild_permissions(manage_guild=True)
    async def utilities(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help("utilities")

    @utilities.command(
        name="rules",
        description="Send the rules embed"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rules(self, ctx: commands.Context):
        guild = ctx.guild or ctx.interaction.guild

        roleIds = [1367825616396619786, 1367825705609728060, 1367825737674920017]
        roles = [guild.get_role(rid) for rid in roleIds if guild.get_role(rid)]

        embed = discord.Embed(
            title="❔ Information",
            description=(
                "Tauri is a groundbreaking multipurpose Discord bot designed to enhance your server's experience. "
                "Seamlessly integrating a variety of features, Tauri offers customizable moderation tools, interactive games, "
                "and advanced user analytics to ensure optimal server management and engagement.\n\n"
                "❕**Guidelines**\n\n"
                "<:arrowright:1368090043000029204> **General Knowledge** – Follow Discord's "
                "[Terms of Service](https://discord.com/terms) and [Community Guidelines](https://discord.com/guidelines).\n"
                "<:arrowright:1368090043000029204> **Use channels appropriately** – Post in the correct channels and avoid spamming.\n"
                "<:arrowright:1368090043000029204> **Advertising** – Refrain from posting any advertisements or self‑promotion.\n"
                "<:arrowright:1368090043000029204> **Report Issues** – Use the designated report channels or contact a moderator."
            ),
            color=None
        )

        view = RoleToggleView(roles)

        await ctx.channel.send(embed=embed, view=view)
        await ctx.send("Embed sent", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        guild = discord.Object(id=tauriServerId)
        self.bot.tree.copy_global_to(guild=guild)
        await self.bot.tree.sync(guild=guild)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utilities(bot))