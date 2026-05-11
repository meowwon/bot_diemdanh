import discord

from datetime import datetime

from core.bot import bot
from core.timezone import TZ

from utils.data_manager import (
    load_data,
    migrate_old_data
)


@bot.tree.command(
    name="dailystats",
    description="Thống kê hôm nay"
)
async def dailystats(interaction: discord.Interaction):

    await interaction.response.defer()

    duty_data = load_data()

    duty_data = migrate_old_data(duty_data)

    today = datetime.now(TZ).date()

    stats = {}

    for user_id, data in duty_data.items():

        stats[user_id] = {
            'username': data.get('username'),
            'total_seconds': 0,
            'sessions': 0
        }

        for session in data.get('history', []):

            start_time = datetime.fromisoformat(
                session['start_time']
            )

            if start_time.date() == today:

                stats[user_id]['total_seconds'] += session.get(
                    'duration_seconds',
                    0
                )

                stats[user_id]['sessions'] += 1

    stats = {
        k: v for k, v in stats.items()
        if v['sessions'] > 0
    }

    if not stats:

        await interaction.followup.send(
            "📊 Hôm nay chưa có ai on-duty"
        )

        return

    sorted_stats = sorted(
        stats.items(),
        key=lambda x: x[1]['total_seconds'],
        reverse=True
    )

    embed = discord.Embed(
        title="📊 THỐNG KÊ HÔM NAY",
        color=0x2ecc71,
        timestamp=datetime.now(TZ)
    )

    for idx, (_, data) in enumerate(sorted_stats, 1):

        hours = int(data['total_seconds'] // 3600)

        minutes = int(
            (data['total_seconds'] % 3600) // 60
        )

        embed.add_field(
            name=f"#{idx} • {data['username']}",
            value=f"⏱️ {hours}h {minutes}m\n📈 {data['sessions']} lần",
            inline=False
        )

    await interaction.followup.send(embed=embed)