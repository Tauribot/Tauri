import os
import discord

staffroles = {
    "1242478342960058459": "Developer",
    "1242478351608844370": "Manager",
    "1242478353269653596": "Support",
    "1242478354930462720": "Staff Team"
 }

staffroleid = [
    1242478342960058459,
    1242478351608844370,
    1242478353269653596,
    1242478354930462720,
]

async def has_role(bot, user):
    guild = await bot.fetch_guild(os.getenv("support_id"))
    member = await guild.fetch_member(user.id)
    filtered = []
    if member:
        for role in member.roles:
            if str(role.id) in staffroles:
                filtered.append(staffroles[str(role.id)])
        return filtered
    return []