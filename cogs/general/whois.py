import discord
from discord.ext import commands
from discord import app_commands
from roblox import Client, AvatarThumbnailType
from roblox.utilities.exceptions import UserNotFound
import typing
import bloxlink
import os
import re
from bloxlink.exceptions import BloxlinkException
from internal.universal.staff import has_role
from internal.universal.emojis import getemojis



class Whois(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.badge_emojis = {}

    async def get_user_badges(self, user: discord.User) -> list[str]:
        badges = []
        flags = user.public_flags

        # Load emojis at the start of the method
        self.badge_emojis = await getemojis()

        # Staff Badges
        if user.id == 570499080187412480:
            badges.append(f"{self.badge_emojis.get('owner')} Owner")
        
        staffroles = await has_role(self, user)
        if "Developer" in staffroles:
            badges.append(f"{self.badge_emojis.get('Developer')} Developer")
        if "Manager" in staffroles:
            badges.append(f"{self.badge_emojis.get('Manager')} Manager")
        if "Support" in staffroles:
            badges.append(f"{self.badge_emojis.get('Support')} Support")

        # Paid Badges
        premium = self.bot.db.premium.find_one({"target_id": user.id, "target_type": "user", "active": True})
        if premium:
            badges.append(f"{self.badge_emojis.get('premium')} Premium")

        # Special Rewards
        blocked = self.bot.db.blocklist.find_one({"user_id": user.id})
        if blocked:
            badges.append(f"{self.badge_emojis.get('blocked')} Blocked User")

        # Other Badges
        if user.bot:
            badges.append(f"{self.badge_emojis.get('bot')} Bot")
        if flags.system:
            badges.append(f"{self.badge_emojis.get('system')} System")
        if flags.staff:
            badges.append(f"{self.badge_emojis.get('staff')} Discord Staff")
        if flags.partner:
            badges.append(f"{self.badge_emojis.get('partner')} Partner")
        if flags.hypesquad:
            badges.append(f"{self.badge_emojis.get('hypesquad')} HypeSquad Events")
        if flags.bug_hunter:
            badges.append(f"{self.badge_emojis.get('bug_hunter')} Bug Hunter")
        if flags.bug_hunter_level_2:
            badges.append(f"{self.badge_emojis.get('bug_hunterv2')} Bug Hunter Level 2")
        if flags.hypesquad_bravery:
            badges.append(f"{self.badge_emojis.get('hypesquad_bravery')} HypeSquad Bravery")
        if flags.hypesquad_brilliance:
            badges.append(f"{self.badge_emojis.get('hypesquad_brilliance')} HypeSquad Brilliance")
        if flags.hypesquad_balance:
            badges.append(f"{self.badge_emojis.get('hypesquad_balance')} HypeSquad Balance")
        if flags.active_developer:
            badges.append(f"{self.badge_emojis.get('active_developer')} Active Developer")

        return badges

    @commands.hybrid_group(
        name="whois",
        description="Get information about a user"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def whois(self, ctx):
        pass

    @whois.command(
        name="discord",
        description="Get information about a user"
    )
    async def dc(self, ctx, user: typing.Optional[typing.Union[discord.Member, discord.User]]):
        await ctx.defer()
        if not user:
            user = ctx.author

        fetched = await self.bot.fetch_user(user.id)
        accent_colour = fetched.accent_colour

        preloading = discord.Embed(
            title="Loading...",
            description="Please wait while we load the user information...",
            color=None
        )
        msg = await ctx.send(embed=preloading)

        embed = discord.Embed(
            color=accent_colour,
            timestamp=ctx.message.created_at
        )
        # Layout the embed
        embed.set_author(name=f"@{user.name}", icon_url=user.avatar)
        if fetched.banner:
            embed.set_image(url=fetched.banner.url)
        embed.set_thumbnail(url=user.avatar)

        # Badges
        badges = await self.get_user_badges(user)
        if badges:
            count = len(badges)
            if count == 0:
                embed.add_field(
                    name=f"Badges [{count}]", value="No badges", inline=False)
            else:
                embed.add_field(
                    name=f"Badges [{count}]", value="\n".join(badges), inline=False)

        # Roblox Collection
        rblx_client = bloxlink.Bloxlink(token=os.getenv("bloxlink"))
        robloxinfo = None
        view = discord.ui.View()
        try:
            roblox_id = rblx_client.global_discord_to_roblox(int(user.id))
            if roblox_id:
                client = Client()
                try:
                    roblox_user = await client.get_user(int(roblox_id))
                    emojis = await getemojis()
                    robloxico = emojis.get("roblox")
                    if roblox_user:
                        robloxinfo = {
                            "user": roblox_user.name,
                            "id": roblox_user.id,
                            "link": f"[{roblox_user.name}](https://www.roblox.com/users/{roblox_user.id}/profile)",
                            "timestamp": f"<t:{int(roblox_user.created.timestamp())}:F>\n[<t:{int(roblox_user.created.timestamp())}:R>]"
                        }

                    if roblox_user.display_name != roblox_user.name:
                        view.add_item(discord.ui.Button(label=f"{roblox_user.display_name} (@{roblox_user.name})", url=f"https://www.roblox.com/users/{roblox_user.id}/profile", emoji=robloxico))
                    else:
                        view.add_item(discord.ui.Button(label=f"@{roblox_user.name}", url=f"https://www.roblox.com/users/{roblox_user.id}/profile", emoji=robloxico))
                except (UserNotFound, ValueError):
                    pass
        except BloxlinkException:
            pass

        # User information
        embed.add_field(
            name="User", value=f"{user.mention} `{user.id}`", inline=False)
        if robloxinfo:
            embed.add_field(
                name="Roblox", value=f"{robloxinfo['link']} `{robloxinfo['id']}`\n{robloxinfo['timestamp']}",
                inline=False)
        embed.add_field(
            name="Created At",
            value=f"<t:{int(user.created_at.timestamp())}:F>\n[<t:{int(user.created_at.timestamp())}:R>]", inline=True)
        if hasattr(user, "joined_at") and user.joined_at:
            embed.add_field(
                name="Joined At",
                value=f"<t:{int(user.joined_at.timestamp())}:F>\n[<t:{int(user.joined_at.timestamp())}:R>]",
                inline=True)

        # Roles
        if isinstance(user, discord.Member):
            roles = sorted(
                [role for role in user.roles if role != ctx.guild.default_role],
                key=lambda r: r.position,
                reverse=True
            )
            if roles:
                count = len(roles)
                if count == 0:
                    embed.add_field(
                        name=f"Roles [{count}]", value="No roles", inline=False)
                else:
                    role_mentions = " ".join(role.mention for role in roles)
                    embed.add_field(
                        name=f"Roles [{count}]", value=role_mentions, inline=False)

        # Permissions
        if isinstance(user, discord.Member):
            try:
                if user.guild_permissions:
                    permissions = user.guild_permissions
                    dangerous_permissions = [
                        "administrator",
                        "ban_members",
                        "kick_members",
                        "manage_guild",
                        "manage_channels",
                        "manage_messages",
                        "manage_roles",
                        "manage_webhooks",
                    ]

                    def prettify(x):
                        return x.replace("_", " ").title()

                    prettydangerous = [
                        prettify(perm) for perm in dangerous_permissions if getattr(permissions, perm)]
                    if prettydangerous:
                        embed.add_field(name="Permissions", value=", ".join(prettydangerous), inline=False)
            except AttributeError:
                pass

        await msg.edit(embed=embed, view=view)


    @whois.command(
        name="roblox",
        description="Get information about a Roblox user"
    )
    async def roblox(self, ctx, roblox: str):
        await ctx.defer()
        client = Client()
        number_pattern = re.compile(r"^\d+$")
        is_number = bool(number_pattern.match(roblox))
        roblox_not_found = discord.Embed(
            title="Not Found",
            description="The user you provided was not found. Double check the username or ID and try again.",
            color=None,
        )
        
        if is_number is True:
            try:
                user = await client.get_user(int(roblox))
            except (UserNotFound, ValueError):
                user = None
            if user:
                output = await handle_user(client, user)

                await ctx.send(embed=output[0], view=output[1])
            elif user is None:
                await ctx.send(embed=roblox_not_found, ephemeral=True)

        elif is_number is False:
            try:
                user = await client.get_user_by_username(roblox)
            except (UserNotFound, ValueError):
                user = None
            if user:
                output = await handle_user(client, user)
                await ctx.send(embed=output[0], view=output[1])
            elif user is None:
                await ctx.send(embed=roblox_not_found, ephemeral=True)
        else:
            await ctx.send(embed=roblox_not_found, ephemeral=True)

async def handle_user(client, user):
    thumbnail = await client.thumbnails.get_user_avatar_thumbnails(
        users=[user],
        type=AvatarThumbnailType.headshot,
        size=(48, 48)
    )
    embed = discord.Embed(
        color=None
    )

    if user.display_name != user.name:
        embed.set_author(name=f"{user.display_name} (@{user.name})", icon_url=thumbnail[0].image_url)
    else:
        embed.set_author(name=f"@{user.name}", icon_url=thumbnail[0].image_url)

    embed.set_thumbnail(url=thumbnail[0].image_url)
    embed.add_field(name="Account", value=f"{user.name} `{user.id}`", inline=False)
    embed.add_field(name="Created At", value=f"<t:{int(user.created.timestamp())}:F>\n[<t:{int(user.created.timestamp())}:R>]", inline=False)


    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="View Profile", url=f"https://www.roblox.com/users/{user.id}/profile"))

    return [embed, view]


async def setup(bot):
    await bot.add_cog(Whois(bot))
