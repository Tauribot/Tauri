import discord
from discord.ext import commands
from discord import app_commands
from internal.universal.emojis import getemojis

"""

Will still be updating this over time, 
adding more customization options (change button color, ...) and fix bugs but this is stable.

"""

infoFields = {
    "serverName": "Server Name",
    "memberCount": "Member Count",
    "creationDate": "Creation Date",
    "boostLevel": "Boost Level",
    "channelCount": "Channel Count",
    "roleCount": "Role Count"
}

defaultConfig = {
    "serverName": True,
    "memberCount": True,
    "creationDate": True,
    "boostLevel": True,
    "channelCount": True,
    "roleCount": True,
    "showLogo": True,
    "showBanner": False,
    "showRoles": True,
    "configured": False, # !!!! Do not set to True !!!!
    "embedColor": None,
    "hasChanges": False # !!!! Do not set to True !!!!
}


class SettingsDropdown(discord.ui.Select):
    def __init__(self, bot, guild_id, configured: bool):
        self.bot = bot
        self.guild_id = guild_id
        self.configured = configured

        options = [
            discord.SelectOption(label="Appearance", value="appearance"),
            discord.SelectOption(label="Content", value="content"),
            discord.SelectOption(label="Skip Config" if not configured else "Reset to Default", value="skip"),
            discord.SelectOption(label="Finish", value="finish")
        ]

        super().__init__(
            placeholder="Choose settings category…",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, bot, guild_id, interaction: discord.Interaction):
        choice = self.values[0]
        cfg = self.bot.db.guildConfigs.find_one({"_id": self.guild_id}) or defaultConfig.copy()

        if choice == "skip":
            defaultConfig = defaultConfig.copy()
            self.bot.db.guildConfigs.update_one(
                {"_id": self.guild_id},
                {"$set": {**defaultConfig, "configured": True, "hasChanges": False}},
                upsert=True
            )
            return await interaction.response.edit_message(
                content="You have skipped the configuration. Basic settings applied.",
                embed=None,
                view=None
            )

        if choice == "finish":
            rec = self.bot.db.guildConfigs.find_one({"_id": self.guild_id})
            if rec.get("hasChanges", False):
                cfg = bot.db.guildConfigs.find_one({"_id": guild_id}) or defaultConfig.copy()
                self.bot.db.guildConfigs.update_one(
                    {"_id": self.guild_id},
                    {"$set": {**cfg, "hasChanges": False}},
                    upsert=True
                )
                return await interaction.response.edit_message(
                    content="Your changes have been saved successfully.",
                    embed=None,
                    view=None
                )
            else:
                if not rec.get("configured", False):
                    basic = defaultConfig.copy()
                    basic["configured"] = True
                    basic["hasChanges"] = False
                    self.bot.db.guildConfigs.update_one(
                        {"_id": self.guild_id},
                        {"$set": basic},
                        upsert=True
                    )
                    return await interaction.response.edit_message(
                        content="No changes were made. I have automatically applied the basic config.",
                        embed=None,
                        view=None
                    )

        if choice == "appearance":
            view = discord.ui.View(timeout=300)
            view.add_item(BackButton(self.bot, self.guild_id))
            view.add_item(ColorButton(self.bot, self.guild_id))
            view.add_item(ToggleLogo(self.bot, self.guild_id))
            view.add_item(ToggleBanner(self.bot, self.guild_id))

        else:
            view = discord.ui.View(timeout=300)
            for key, label in infoFields.items():
                view.add_item(ToggleField(self.bot, self.guild_id, key, label))
            view.add_item(ToggleField(self.bot, self.guild_id, "showRoles", "Display Roles"))
            view.add_item(ResetButton(self.bot, self.guild_id))
            view.add_item(BackButton(self.bot, self.guild_id))

        settingsSelect = discord.Embed(
            title="Settings",
            description=(
                "Use the menu below to configure the server info display to your liking. If any errors occur, contact Tauri support in our Discord server with the /help command."
            ),
            color=cfg.get("embedColor") if cfg.get("embedColor") else None
        )

        await interaction.response.edit_message(content=None, embed=settingsSelect, view=view)

class SettingsView(discord.ui.View):
    def __init__(self, bot: commands.Bot, guild_id: int, current_config: dict):
        super().__init__(timeout=300)
        self.add_item(SettingsDropdown(bot, guild_id, current_config.get("configured", False)))
        
class ColorButton(discord.ui.Button):
    def __init__(self, bot, guild_id):
        super().__init__(label="Set Color", style=discord.ButtonStyle.primary)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ColorModal(self.bot, self.guild_id))
class ConfirmButton(discord.ui.Button):
    def __init__(self, bot, guild_id):
        super().__init__(label="Finish", style=discord.ButtonStyle.success)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        self.bot.db.guildConfigs.update_one(
            {"_id": self.guild_id},
            {"$set": {"configured": True, "hasChanges": False}},
            upsert=True
        )
        await interaction.response.edit_message(
            content="Configuration completed. You can now use /serverinfo normally.",
            embed=None,
            view=None
        )

class ConfigureButton(discord.ui.Button):
    def __init__(self, bot, guild_id):
        super().__init__(label="Configure", style=discord.ButtonStyle.blurple)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        cfg = self.bot.db.guildConfigs.find_one({"_id": self.guild_id}) or defaultConfig.copy()
        view = SettingsView(self.bot, self.guild_id, cfg)
        settingsSelect = discord.Embed(
            title="Settings",
            description=(
                "Use the buttons below to configure the server info display to your liking. If any errors occur, contact Tauri support in our Discord server with the /help command."
            ),
            color=cfg.get("embedColor") if cfg.get("embedColor") else None
        )
        await interaction.response.edit_message(
            content=None,
            embed=settingsSelect,
            view=view
        )

class ColorModal(discord.ui.Modal):
    def __init__(self, bot, guild_id):
        super().__init__(title="Set Embed Color")
        self.bot = bot
        self.guild_id = guild_id
        self.hex_input = discord.ui.TextInput(
            label="Hex Color",
            placeholder="#FF0000",
            max_length=7
        )
        self.add_item(self.hex_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            raw = self.hex_input.value.strip()

            if not raw.startswith("#") or len(raw) != 7:
                return await interaction.response.send_message(
                    "Please enter a valid hex color in the format #RRGGBB.",
                    ephemeral=True
                )

            hex_value = raw[1:]
            try:
                color_int = int(hex_value, 16)
            except ValueError:
                return await interaction.response.send_message(
                    "That doesn't look like a valid hexadecimal color.",
                    ephemeral=True
                )

            self.bot.db.guildConfigs.update_one(
                {"_id": self.guild_id},
                {"$set": {
                    "embedColor": color_int,
                    "configured": True,
                    "hasChanges": True
                }},
                upsert=True
            )
            await interaction.response.send_message("Embed color updated.", ephemeral=True)

        except Exception as e:
            print(f"[ColorModal Error] {e}")
            await interaction.response.send_message(
                "An unexpected error occurred. Please try again.",
                ephemeral=True
            )

class ToggleLogo(discord.ui.Button):
    def __init__(self, bot, guild_id):
        super().__init__(label="Toggle Server Logo", style=discord.ButtonStyle.secondary)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        cfg = self.bot.db.guildConfigs.find_one({"_id": self.guild_id}) or {}
        cfg["showLogo"] = not cfg.get("showLogo", True)
        cfg["configured"] = True
        cfg["hasChanges"] = True
        self.bot.db.guildConfigs.update_one(
            {"_id": self.guild_id}, {"$set": cfg}, upsert=True
        )
        await interaction.response.send_message(
            f"Logo Display {'Enabled' if cfg['showLogo'] else 'Disabled'}.", ephemeral=True
        )

class ToggleBanner(discord.ui.Button):
    def __init__(self, bot, guild_id):
        super().__init__(label="Toggle Server Banner", style=discord.ButtonStyle.secondary)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild or not guild.banner:
            return await interaction.response.send_message("No banner available.", ephemeral=True)
        cfg = self.bot.db.guildConfigs.find_one({"_id": self.guild_id}) or {}
        cfg["showBanner"] = not cfg.get("showBanner", False)
        cfg["configured"] = True
        cfg["hasChanges"] = True
        self.bot.db.guildConfigs.update_one(
            {"_id": self.guild_id}, {"$set": cfg}, upsert=True
        )
        await interaction.response.send_message(
            f"Banner Display {'Enabled' if cfg['showBanner'] else 'Disabled'}.", ephemeral=True
        )

class ToggleField(discord.ui.Button):
    def __init__(self, bot, guild_id, config_key: str, label: str):
        cfg = bot.db.guildConfigs.find_one({"_id": guild_id}) or defaultConfig.copy()
        current = cfg.get(config_key, True)
        super().__init__(
            label=f"{label}: {'On' if current else 'Off'}",
            style=discord.ButtonStyle.success if current else discord.ButtonStyle.danger
        )
        self.bot = bot
        self.guild_id = guild_id
        self.config_key = config_key

    async def callback(self, interaction: discord.Interaction):
        cfg = self.bot.db.guildConfigs.find_one({"_id": self.guild_id}) or defaultConfig.copy()
        new_val = not cfg.get(self.config_key, True)
        self.bot.db.guildConfigs.update_one(
            {"_id": self.guild_id},
            {"$set": {
                self.config_key: new_val,
                "configured": True,
                "hasChanges": True
            }},
            upsert=True
        )
        view = discord.ui.View(timeout=300)
        for key, label in infoFields.items():
            view.add_item(ToggleField(self.bot, self.guild_id, key, label))
        view.add_item(ToggleField(self.bot, self.guild_id, "showRoles", "Display Roles"))
        view.add_item(ResetButton(self.bot, self.guild_id))
        view.add_item(BackButton(self.bot, self.guild_id))
        await interaction.response.edit_message(content="Content Settings:", embed=None, view=view)

class ResetButton(discord.ui.Button):
    def __init__(self, bot, guild_id):
        super().__init__(label="Reset to Defaults", style=discord.ButtonStyle.danger)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        basic = defaultConfig.copy()
        basic["configured"] = False
        basic["hasChanges"] = False
        self.bot.db.guildConfigs.update_one(
            {"_id": self.guild_id}, {"$set": basic}, upsert=True
        )
        view = SettingsView(self.bot, self.guild_id, basic)
        await interaction.response.edit_message(content="Settings reset to defaults.", embed=None, view=None, ephemeral=True)

class BackButton(discord.ui.Button):
    def __init__(self, bot, guild_id):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        cfg = self.bot.db.guildConfigs.find_one({"_id": self.guild_id}) or defaultConfig.copy()
        view = SettingsView(self.bot, self.guild_id, cfg)
        settingsSelect = discord.Embed(
            title="Settings",
            description=(
                "Use the menu below to configure the server info display to your liking. If any errors occur, contact Tauri support in our Discord server with the /help command."
            ),
            color=cfg.get("embedColor") if cfg.get("embedColor") else None
        )
        await interaction.response.edit_message(content=None, embed=settingsSelect, view=view)

class ServerInfo(commands.Cog):
    def __init__(self, bot, emojis):
        self.bot = bot
        self.emojis = emojis

    @commands.hybrid_command(name="serverinfo", description="Display server information")
    @app_commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        cfg = self.bot.db.guildConfigs.find_one({"_id": ctx.guild.id}) or defaultConfig.copy()

        if not cfg.get("configured") and ctx.author.guild_permissions.manage_guild:
            view = SettingsView(self.bot, ctx.guild.id, cfg)
            embed = discord.Embed(
                title="Server Information Setup Required",
                description=(
                    "This command hasn't been configured yet. Use the dropdown below to set it up. "
                    "If you need help, run /help and contact Tauri support."
                ),
                color=cfg.get("embedColor") if cfg.get("embedColor") else None
            )
            return await ctx.send(embed=embed, view=view, ephemeral=True)

        badges = []
        premium_data = self.bot.db.premium.find_one({
            "target_id": str(ctx.guild.id),
            "target_type": "guild",
            "active": True
        })
        if premium_data:
            badges.append(f"{self.emojis.get('owner')} This is a Premium Tauri server!")

        embed = discord.Embed(
            title="Server Information",
            description=" • ".join(badges) if badges else None,
            color=cfg.get("embedColor") if cfg.get("embedColor") else None
        )

        if cfg.get("showLogo") and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        if cfg.get("showBanner") and ctx.guild.banner:
            embed.set_image(url=ctx.guild.banner.url)
        if cfg.get("serverName"):
            embed.add_field(name="Server Name", value=f"{ctx.guild.name} {ctx.guild.id}", inline=False)
        if cfg.get("memberCount"):
            embed.add_field(name="Member Count", value=str(ctx.guild.member_count), inline=False)
        if cfg.get("creationDate"):
            ts = int(ctx.guild.created_at.timestamp())
            embed.add_field(name="Creation Date", value=f"<t:{ts}:D> (<t:{ts}:R>)", inline=False)
        if cfg.get("boostLevel"):
            embed.add_field(name="Boost Level", value=f"Level {ctx.guild.premium_tier}", inline=False)
        if cfg.get("channelCount"):
            embed.add_field(name="Channel Count", value=str(len(ctx.guild.channels)), inline=False)
        if cfg.get("roleCount"):
            embed.add_field(name="Role Count", value=str(len(ctx.guild.roles)), inline=False)
        if cfg.get("showRoles"):
            filtered = [
                role for role in ctx.guild.roles
                if role != ctx.guild.default_role and any(c.isalpha() for c in role.name)
            ]
            shown = filtered[:10]
            hidden = len(filtered) - len(shown)
            mentions = [r.mention for r in shown]
            if hidden > 0:
                mentions.append(f"and {hidden} more…")
            embed.add_field(name="Roles", value=" ".join(mentions), inline=False)

        view = None
        if ctx.author.guild_permissions.manage_guild:
            view = discord.ui.View()
            view.add_item(ConfigureButton(self.bot, ctx.guild.id))

        await ctx.send(embed=embed, view=view)

    """ This was just for testing but if you want it just comment it in.

    @commands.hybrid_command(name="resetconfig", description="Reset the serverinfo configuration for this server.")
    @app_commands.guild_only()
    async def resetconfig(self, ctx: commands.Context):
        basic = defaultConfig.copy()
        basic["configured"] = False
        basic["hasChanges"] = False
        self.bot.db.guildConfigs.update_one(
            {"_id": ctx.guild.id}, {"$set": basic}, upsert=True
        )
        await ctx.send(f"Configuration for guild {ctx.guild.id} has been reset to default.", ephemeral=True)
    
    """
async def setup(bot):
    emojis = await getemojis()
    await bot.add_cog(ServerInfo(bot, emojis))