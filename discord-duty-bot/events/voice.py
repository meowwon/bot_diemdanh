from core.bot import bot

from utils.activity_manager import log_activity


@bot.event
async def on_voice_state_update(member, before, after):

    if before.channel != after.channel:

        if after.channel:

            log_activity(
                member.id,
                'voice_join',
                f'Tham gia: {after.channel.name}'
            )

        elif before.channel:

            log_activity(
                member.id,
                'voice_leave',
                f'Rời: {before.channel.name}'
            )