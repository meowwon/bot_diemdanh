from discord.ext import tasks
from datetime import datetime

import discord

from core.bot import bot
from core.timezone import TZ

from utils.data_manager import load_data, migrate_old_data
from views.confirm_view import ConfirmOnDutyView


@tasks.loop(hours=3)
async def check_onduty_status():

    duty_data = load_data()

    duty_data = migrate_old_data(duty_data)

    for user_id_str, data in duty_data.items():

        if data.get('current_status') == 'on-duty':

            user = bot.get_user(int(user_id_str))

            if user:

                try:

                    start_time = datetime.fromisoformat(
                        data['current_session']['start_time']
                    )

                    duration = datetime.now(TZ) - start_time

                    hours = int(duration.total_seconds() // 3600)

                    minutes = int(
                        (duration.total_seconds() % 3600) // 60
                    )

                    embed = discord.Embed(
                        title="🔔 Xác Nhận On-Duty",
                        description=f"Bạn đã làm việc {hours}h {minutes}m",
                        color=0xFFA500,
                        timestamp=datetime.now(TZ)
                    )

                    view = ConfirmOnDutyView(int(user_id_str))

                    await user.send(
                        embed=embed,
                        view=view
                    )

                except Exception as e:
                    print(e)