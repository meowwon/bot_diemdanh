from core.bot import bot

from tasks.onduty_checker import check_onduty_status


@bot.event
async def on_ready():

    print(f'✅ {bot.user}')

    try:

        synced = await bot.tree.sync()

        print(f'🔄 {len(synced)} slash commands')

        if not check_onduty_status.is_running():
            check_onduty_status.start()

    except Exception as e:
        print(e)