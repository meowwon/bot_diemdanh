import discord

from discord import app_commands

from datetime import datetime

from core.bot import bot
from core.timezone import TZ

from utils.data_manager import (
    load_data,
    migrate_old_data
)


@bot.tree.command(
    name="checkstats",
    description="Xem thống kê"
)
@app_commands.describe(
    thang="Tháng",
    nam="Năm"
)
async def checkstats(
    interaction: discord.Interaction,
    thang: int,
    nam: int
):

    await interaction.response.defer()

    duty_data = load_data()

    duty_data = migrate_old_data(duty_data)

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

            if (
                start_time.month == thang
                and start_time.year == nam
            ):

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
            "❌ Không có dữ liệu"
        )

        return

    sorted_stats = sorted(
        stats.items(),
        key=lambda x: x[1]['total_seconds'],
        reverse=True
    )

    embed = discord.Embed(
        title=f"📊 THỐNG KÊ {thang}/{nam}",
        color=0xf1c40f,
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