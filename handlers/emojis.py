import os

async def getemojis():
    """Load emojis"""
    os.getenv("environment")
    emojislist = {}
    if os.getenv("environment") == "development":
        emojislist = {
            'owner': '<:owner:1350916374041727127>',
            'bot': '<:bot:1350916484909633618>',
            'staff': '<:staff:1350916500214513745>',
            'system': '<:system:1350916330144010241>',
            'partner': '<:partner:1350916409596711022>',
            'hypesquad': '<:hypesquad:1350916315682181220>',
            'bug_hunter': '<:bug:1350916452559097857>',
            'bug_hunterv2': '<:bugv2:1350916468883066992>',
            'hypesquad_bravery': '<:bravery:1350916271381938268>',
            'hypesquad_brilliance': '<:brilliance:1350916257612042351>',
            'hypesquad_balance': '<:balance:1350916394794876982>',
            'active_developer': '<:activedev:1350916219829620777>',
            'roblox': '<:roblox:1351674923365437595>',
        }
    elif os.getenv("environment") == "production":
        emojislist = {
            'owner': '<:owner:1350915181810684096>',
            'bot': '<:bot:1350915281123541133>',
            'staff': '<:staff:1350915264736133122>',
            'system': '<:system:1350917310818422838>',
            'partner': '<:partner:1350915348680933546>',
            'hypesquad': '<:hypesquad:1350915139792277559>',
            'bug_hunter': '<:bugv1:1350915314690297866>',
            'bug_hunterv2': '<:bugv2:1350915329248985189>',
            'hypesquad_bravery': '<:bravery:1350915004689551503>',
            'hypesquad_brilliance': '<:brilliance:1350915016731398154>',
            'hypesquad_balance': '<:balance:1350915208620675304>',
            'active_developer': '<:activedev:1350914986540662784>',
            'roblox': '<:roblox:1351674629575544872>',
        }
    return emojislist