import discord


def is_playing_gta(member: discord.Member) -> bool:

    if not member.activities:
        return False

    for activity in member.activities:

        if isinstance(activity, discord.Game) or isinstance(activity, discord.Activity):

            if activity.name and "GTA5VN" in activity.name:
                return True

    return False