import discord
from discord import app_commands
from datetime import datetime

from core.bot import bot
from utils.data_manager import load_data, migrate_old_data
from core.timezone import TZ


@bot.tree.command(
    name="checkprofile",
    description="Kiểm tra hồ sơ on-duty theo khoảng thời gian"
)
@app_commands.describe(
    member="Người cần kiểm tra",
    from_date="Ngày bắt đầu (dd/mm/yyyy)",
    to_date="Ngày kết thúc (dd/mm/yyyy)"
)
async def checkprofile(
    interaction: discord.Interaction,
    member: discord.Member,
    from_date: str,
    to_date: str
):
    await interaction.response.defer()

    try:
        start_date = datetime.strptime(from_date, "%d/%m/%Y")
        end_date = datetime.strptime(to_date, "%d/%m/%Y")

        start_date = start_date.replace(
            hour=0,
            minute=0,
            second=0,
            tzinfo=TZ
        )

        end_date = end_date.replace(
            hour=23,
            minute=59,
            second=59,
            tzinfo=TZ
        )

    except:
        await interaction.followup.send(
            "❌ Format ngày phải là: dd/mm/yyyy",
            ephemeral=True
        )
        return

    duty_data = load_data()
    duty_data = migrate_old_data(duty_data)

    user_id = str(member.id)

    if user_id not in duty_data:
        await interaction.followup.send(
            "❌ Người này chưa có dữ liệu duty.",
            ephemeral=True
        )
        return

    history = duty_data[user_id].get("history", [])

    total_seconds = 0
    total_sessions = 0

    session_lines = []

    for session in history:
        session_start = datetime.fromisoformat(session['start_time'])
        session_end = datetime.fromisoformat(session['end_time'])

        if session_start.tzinfo is None:
            session_start = session_start.replace(tzinfo=TZ)

        if session_end.tzinfo is None:
            session_end = session_end.replace(tzinfo=TZ)

        if session_start <= end_date and session_end >= start_date:

            duration = session.get("duration_seconds", 0)

            total_seconds += duration
            total_sessions += 1

            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)

            session_lines.append(
                f"• {session_start.strftime('%d/%m %H:%M')} "
                f"→ {session_end.strftime('%d/%m %H:%M')} "
                f"({hours}h {minutes}m)"
            )

    total_hours = int(total_seconds // 3600)
    total_minutes = int((total_seconds % 3600) // 60)

    embed = discord.Embed(
        title="📁 HỒ SƠ ON-DUTY",
        color=0x00BFFF,
        timestamp=datetime.now(TZ)
    )

    embed.add_field(
        name="👤 Nhân viên",
        value=f"```{member.name}```",
        inline=False
    )

    embed.add_field(
        name="📅 Khoảng thời gian",
        value=f"```{from_date} → {to_date}```",
        inline=False
    )

    embed.add_field(
        name="📊 Tổng số ca",
        value=f"```{total_sessions} ca```",
        inline=True
    )

    embed.add_field(
        name="⏱️ Tổng thời gian",
        value=f"```{total_hours}h {total_minutes}m```",
        inline=True
    )

    if session_lines:
        embed.add_field(
            name="📋 Chi tiết ca trực",
            value="\n".join(session_lines[:15]),
            inline=False
        )
    else:
        embed.add_field(
            name="📋 Chi tiết ca trực",
            value="Không có dữ liệu",
            inline=False
        )

    embed.set_footer(text="LM | Profile Duty System")

    await interaction.followup.send(embed=embed)