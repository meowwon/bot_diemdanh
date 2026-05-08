from core.bot import bot

from utils.activity_manager import log_activity


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    channel_name = (
        message.channel.name
        if hasattr(message.channel, 'name')
        else 'DM'
    )

    log_activity(
        message.author.id,
        'message',
        f'Kênh: {channel_name}'
    )

    await bot.process_commands(message)