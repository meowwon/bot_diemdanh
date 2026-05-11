import discord
from discord import app_commands
from datetime import datetime, timedelta
from collections import defaultdict

from core.bot import bot
from utils.data_manager import load_data, migrate_old_data
from core.timezone import TZ
from utils.chart_pro import create_activity_chart_pro


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

    # ===== PARSE DATE =====
    try:
        start_date = datetime.strptime(from_date, "%d/%m/%Y").replace(
            hour=0, minute=0, second=0, tzinfo=TZ
        )

        end_date = datetime.strptime(to_date, "%d/%m/%Y").replace(
            hour=23, minute=59, second=59, tzinfo=TZ
        )
    except:
        await interaction.followup.send(
            "❌ Format ngày phải là: dd/mm/yyyy",
            ephemeral=True
        )
        return

    # ===== LOAD DATA =====
    duty_data = migrate_old_data(load_data())
    user_id = str(member.id)

    if user_id not in duty_data:
        await interaction.followup.send(
            "❌ Người này chưa có dữ liệu duty.",
            ephemeral=True
        )
        return

    history = duty_data[user_id].get("history", [])

    # ===== PROCESS (OPTIMIZED) =====
    daily_stats = defaultdict(lambda: {
        "seconds": 0,
        "sessions": 0,
        "lines": []
    })

    for session in history:
        try:
            session_start = datetime.fromisoformat(session['start_time'])
            session_end = datetime.fromisoformat(session['end_time'])
        except:
            continue

        if session_start.tzinfo is None:
            session_start = session_start.replace(tzinfo=TZ)
        if session_end.tzinfo is None:
            session_end = session_end.replace(tzinfo=TZ)

        # skip nhanh
        if session_end < start_date or session_start > end_date:
            continue

        # clamp range
        start = max(session_start, start_date)
        end = min(session_end, end_date)

        current_day = start.date()
        end_day = end.date()

        while current_day <= end_day:
            day_start = datetime.combine(current_day, datetime.min.time(), tzinfo=TZ)
            day_end = datetime.combine(current_day, datetime.max.time(), tzinfo=TZ)

            seg_start = max(start, day_start)
            seg_end = min(end, day_end)

            if seg_start < seg_end:
                duration = (seg_end - seg_start).total_seconds()
                key = current_day.strftime("%d/%m/%Y")

                daily_stats[key]["seconds"] += duration
                daily_stats[key]["sessions"] += 1

                h = int(duration // 3600)
                m = int((duration % 3600) // 60)

                daily_stats[key]["lines"].append(
                    f"• {seg_start.strftime('%H:%M')} → {seg_end.strftime('%H:%M')} ({h}h {m}m)"
                )

            current_day += timedelta(days=1)

    # ===== EMBED =====
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

    # ===== DATA DISPLAY =====
    if not daily_stats:
        embed.add_field(
            name="📋 Dữ liệu",
            value="Không có dữ liệu",
            inline=False
        )
        await interaction.followup.send(embed=embed)
        return

    # sort chuẩn theo ngày
    sorted_days = sorted(
        daily_stats.items(),
        key=lambda x: datetime.strptime(x[0], "%d/%m/%Y")
    )

    for day, data in sorted_days:
        h = int(data["seconds"] // 3600)
        m = int((data["seconds"] % 3600) // 60)

        embed.add_field(
            name=f"📅 {day} • {h}h {m}m • {data['sessions']} ca",
            value="\n".join(data["lines"][:10]),
            inline=False
        )

    embed.set_footer(text="LM | Profile Duty System")

    # ===== CHART PRO =====
    chart_buffer = create_activity_chart_pro(dict(sorted_days))
    file = discord.File(chart_buffer, filename="activity.png")

    embed.set_image(url="attachment://activity.png")

    await interaction.followup.send(embed=embed, file=file)