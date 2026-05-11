import discord

from datetime import datetime

from core.bot import bot
from core.timezone import TZ

from utils.data_manager import get_user_data


@bot.tree.command(
    name="myduty",
    description="Thông tin duty cá nhân"
)
async def myduty(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=True)

    duty_data, user_id_str = get_user_data(
        interaction.user.id
    )

    data = duty_data[user_id_str]

    total_seconds = 0

    for session in data.get('history', []):

        total_seconds += session.get(
            'duration_seconds',
            0
        )

    if (
        data['current_status'] == 'on-duty'
        and data['current_session']
    ):

        start_time = datetime.fromisoformat(
            data['current_session']['start_time']
        )

        duration = (
            datetime.now(TZ) - start_time
        ).total_seconds()

        total_seconds += duration

    hours = int(total_seconds // 3600)

    minutes = int(
        (total_seconds % 3600) // 60
    )

    embed = discord.Embed(
        title="📋 DUTY CỦA BẠN",
        color=0x00bfff,
        timestamp=datetime.now(TZ)
    )

    embed.add_field(
        name="👤 Username",
        value=interaction.user.name,
        inline=False
    )

    embed.add_field(
        name="📊 Trạng thái",
        value=data['current_status'],
        inline=False
    )

    embed.add_field(
        name="⏱️ Tổng thời gian",
        value=f"{hours}h {minutes}m",
        inline=False
    )

    embed.add_field(
        name="📈 Tổng số lần",
        value=str(len(data.get('history', []))),
        inline=False
    )

    await interaction.followup.send(
        embed=embed,
        ephemeral=True
    )