import discord
from discord.ext import commands
from internal.universal.emojis import getemojis

class Welcome(commands.Cog):
    def __init__(self, bot, emojis):
        self.bot = bot
        self.emojis = emojis
        # Put it in env if you can, I can't access it.
        self.supportServerId = 1242439573254963292
        self.welcomeChannelId = 1367543259982725301
        self.unverifiedRoleId = 1367627062826897471

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != self.supportServerId:
            return

        try:
            message = (
                f"We are glad to have you here {member.mention}! "
                f"You are member `#{member.guild.member_count}.` "
                "Please make sure to check out the rules and verify yourself "
                "before chatting here. We do not want you to get moderated."
            )

            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Rules",
                url="https://discord.com/channels/1242439573254963292/1351328861190750320"
            ))
            view.add_item(discord.ui.Button(
                label="Verify", 
                url="https://discord.com/channels/1242439573254963292/1367629064579580027"
            ))

            channel = self.bot.get_channel(self.welcomeChannelId)
            if channel:
                await channel.send(content=message, view=view)
            else:
                print(f"Welcome channel not found: {self.welcomeChannelId}")

            if unverifiedRole := member.guild.get_role(self.unverifiedRoleId):
                try:
                    await member.add_roles(unverifiedRole, reason="New member joined")
                except discord.Forbidden:
                    print(f"Missing permissions to assign {unverifiedRole.name} to {member}")
            else:
                print(f"Unverified role not found: {self.unverifiedRoleId}")

        except Exception as e:
            print(f"Error in welcome system: {e}")

async def setup(bot):
    emojis = await getemojis()
    await bot.add_cog(Welcome(bot, emojis))