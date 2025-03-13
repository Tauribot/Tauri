import discord
from discord.ext import commands
from discord import app_commands
import typing

class Whois(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.badge_emojis = {
            'staff': '<:staff:1349764059246891159>',
            'partner': '<:partner:1349764050946359338>',
            'hypesquad': '<:hypesquad:1349764041735667762>',
            'bug_hunter': '<:bug1:1349764053081395342>',
            'hypesquad_bravery': '<:bravery:1349764032684363818>',
            'hypesquad_brilliance': '<:brillance:1349764035171586101>',
            'hypesquad_balance': '<:balance:1349764048291631238>',
            'active_developer': '<:activedev:1349765304087085077>',
        }

    def get_user_badges(self, user: discord.User) -> list[str]:
        badges = []
        flags = user.public_flags
        
        if flags.staff:
            badges.append(f"{self.badge_emojis.get('staff')} Discord Staff")
        if flags.partner:
            badges.append(f"{self.badge_emojis.get('partner')} Partner")
        if flags.hypesquad:
            badges.append(f"{self.badge_emojis.get('hypesquad')} HypeSquad Events")
        if flags.bug_hunter:
            badges.append(f"{self.badge_emojis.get('bug_hunter')} Bug Hunter")
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
    async def whois(self, ctx):
        await ctx.reply("The `whois` command requires a subcommand. Use `/whois discord` to get information about a discord user.")
        pass

    @whois.command(
        name="discord",
        description="Get information about a user"
    )
    async def dc(self, ctx, user: typing.Optional[typing.Union[discord.Member, discord.User]]):
        if not user:
            user = ctx.author
        
        fetched = await self.bot.fetch_user(user.id)
        accent_colour = fetched.accent_colour

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
        badges = self.get_user_badges(user)
        if badges:
            count = len(badges)
            if count == 0:
                embed.add_field(name=f"Badges [{count}]", value="No badges", inline=False)
            else:
                embed.add_field(name=f"Badges [{count}]", value="\n".join(badges), inline=False)

        # User information
        embed.add_field(name="User", value=f"{user.mention} `{user.id}`", inline=False)
        embed.add_field(name="Created At", value=f"<t:{int(user.created_at.timestamp())}:F>\n[<t:{int(user.created_at.timestamp())}:R>]", inline=True)
        if hasattr(user, "joined_at") and user.joined_at:
            embed.add_field(name="Joined At", value=f"<t:{int(user.joined_at.timestamp())}:F>\n[<t:{int(user.joined_at.timestamp())}:R>]", inline=True)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Whois(bot))