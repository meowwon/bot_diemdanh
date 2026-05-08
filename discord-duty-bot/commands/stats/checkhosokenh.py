import discord
from discord import app_commands
from datetime import datetime

from core.bot import bot
from core.timezone import TZ


@bot.tree.command(
    name="checkchannelprofile",
    description="Kiểm tra số hồ sơ của toàn bộ người trong kênh"
)
@app_commands.describe(
    from_date="Ngày bắt đầu dd/mm/yyyy",
    to_date="Ngày kết thúc dd/mm/yyyy"
)
async def checkchannelprofile(
    interaction: discord.Interaction,
    from_date: str,
    to_date: str
):

    await interaction.response.defer()

    try:

        start_date = datetime.strptime(
            from_date,
            "%d/%m/%Y"
        ).replace(
            hour=0,
            minute=0,
            second=0,
            tzinfo=TZ
        )

        end_date = datetime.strptime(
            to_date,
            "%d/%m/%Y"
        ).replace(
            hour=23,
            minute=59,
            second=59,
            tzinfo=TZ
        )

    except:
        await interaction.followup.send(
            "❌ Format ngày phải là dd/mm/yyyy",
            ephemeral=True
        )
        return

    channel = interaction.channel

    user_profiles = {}
    total_profiles = 0

    async for message in channel.history(limit=None):

        if message.author.bot:
            continue

        msg_time = message.created_at.astimezone(TZ)

        if start_date <= msg_time <= end_date:

            total_profiles += 1

            user_id = str(message.author.id)

            if user_id not in user_profiles:

                user_profiles[user_id] = {
                    "name": message.author.display_name,
                    "count": 0
                }

            user_profiles[user_id]["count"] += 1

    sorted_users = sorted(
        user_profiles.values(),
        key=lambda x: x["count"],
        reverse=True
    )

    embed = discord.Embed(
        title="📁 THỐNG KÊ HỒ SƠ",
        color=0x00BFFF,
        timestamp=datetime.now(TZ)
    )

    embed.add_field(
        name="📅 Khoảng thời gian",
        value=f"```{from_date} → {to_date}```",
        inline=False
    )

    embed.add_field(
        name="📊 Tổng hồ sơ toàn kênh",
        value=f"```{total_profiles} hồ sơ```",
        inline=False
    )

    result_text = ""

    for idx, user in enumerate(sorted_users[:20], start=1):

        medal = "🥇"

        if idx == 2:
            medal = "🥈"

        elif idx == 3:
            medal = "🥉"

        elif idx > 3:
            medal = "📄"

        result_text += (
            f"{medal} "
            f"{user['name']} — "
            f"{user['count']} hồ sơ\n"
        )

    if not result_text:
        result_text = "Không có dữ liệu"

    embed.add_field(
        name="👥 Danh sách hồ sơ",
        value=result_text,
        inline=False
    )

    embed.set_footer(
        text="LM | Channel Profile System"
    )

    await interaction.followup.send(embed=embed)