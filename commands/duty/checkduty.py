import discord

from datetime import datetime

from core.bot import bot
from core.timezone import TZ

from utils.data_manager import (
    load_data,
    migrate_old_data
)


@bot.tree.command(
    name="checkduty",
    description="Xem danh sách on-duty"
)
async def checkduty(interaction: discord.Interaction):

    await interaction.response.defer()

    duty_data = load_data()

    duty_data = migrate_old_data(duty_data)

    on_duty_members = []

    for user_id, data in duty_data.items():

        if data.get('current_status') == 'on-duty':

            start_time = datetime.fromisoformat(
                data['current_session']['start_time']
            )

            duration = datetime.now(TZ) - start_time

            hours = int(duration.total_seconds() // 3600)

            minutes = int(
                (duration.total_seconds() % 3600) // 60
            )

            on_duty_members.append({
                'username': data.get('username'),
                'duration': f'{hours}h {minutes}m',
                'status': data['current_session'].get(
                    'discord_status',
                    'Unknown'
                )
            })

    if not on_duty_members:

        await interaction.followup.send(
            "📋 Không có ai on-duty"
        )

        return

    embed = discord.Embed(
        title="📋 DANH SÁCH ON-DUTY",
        color=0x3498db,
        timestamp=datetime.now(TZ)
    )

    for idx, member in enumerate(on_duty_members, 1):

        embed.add_field(
            name=f"#{idx} • {member['username']}",
            value=f"⏱️ {member['duration']}\n📊 {member['status']}",
            inline=False
        )

    await interaction.followup.send(embed=embed)