import discord

from discord import app_commands

from datetime import datetime

from core.bot import bot
from core.timezone import TZ

from utils.data_manager import (
    get_user_data,
    save_data
)

from utils.activity_manager import log_activity


@bot.tree.command(
    name="offduty",
    description="Off duty"
)
async def offduty(interaction: discord.Interaction):

    await interaction.response.defer()

    duty_data, user_id_str = get_user_data(interaction.user.id)

    if duty_data[user_id_str]['current_status'] != 'on-duty':

        await interaction.followup.send(
            "❌ Bạn chưa on-duty",
            ephemeral=True
        )

        return

    current_session = duty_data[user_id_str]['current_session']

    start_time = datetime.fromisoformat(
        current_session['start_time']
    )

    end_time = datetime.now(TZ)

    duration = end_time - start_time

    hours = int(duration.total_seconds() // 3600)

    minutes = int(
        (duration.total_seconds() % 3600) // 60
    )

    duty_data[user_id_str]['history'].append({
        'start_time': current_session['start_time'],
        'end_time': end_time.isoformat(),
        'duration_seconds': duration.total_seconds(),
        'evidence_image': current_session.get('evidence_image'),
        'discord_status': current_session.get('discord_status')
    })

    duty_data[user_id_str]['current_status'] = 'off-duty'
    duty_data[user_id_str]['current_session'] = None

    save_data(duty_data)

    log_activity(
        interaction.user.id,
        'duty_off',
        f'{hours}h {minutes}m'
    )

    await interaction.followup.send(
        f"🔴 OFF-DUTY sau {hours}h {minutes}m"
    )