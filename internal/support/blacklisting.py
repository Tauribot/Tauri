import discord

async def can_blacklist(ctx, user):
    userid = int(str(user.id))
    failure = discord.Embed(
        title="Block Failed",
        description=f"Failed to block {user} ({userid})",
        colour=None
    )

    if not user:
        failure.description = f"{failure.description}\n```User not found```"
        await ctx.send(embed=failure)
        return False

    if any(role.name == "Blacklist Manager" for role in user.roles):
        failure.description = f"{failure.description}\n```Cannot blacklist a Blacklist Manager```"
        await ctx.send(embed=failure)
        return False

    if any(role.name == "Support Team" for role in user.roles):
        failure.description = f"{failure.description}\n```Cannot blacklist a Support Team member```"
        await ctx.send(embed=failure)
        return False

    if user.id == ctx.author.id:
        failure.description = f"{failure.description}\n```Cannot blacklist yourself```"
        await ctx.send(embed=failure)
        return False

    if user.id == ctx.bot.user.id:
        failure.description = f"{failure.description}\n```Cannot blacklist myself```"
        await ctx.send(embed=failure)
        return False

    return True