import os
import discord

async def has_role(bot, user):
    staffroles = {
        "1242478342960058459": "Developer",
        "1242478351608844370": "Manager",
        "1242478353269653596": "Support"
    }

    guild = await bot.fetch_guild(os.getenv("support_id"))
    member = await guild.fetch_member(user.id)
    filtered = []
    if member:
        for role in member.roles:
            if str(role.id) in staffroles:
                filtered.append(staffroles[str(role.id)])
        return filtered
    return []