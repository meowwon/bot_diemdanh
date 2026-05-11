import discord

from datetime import datetime

from core.bot import bot
from core.timezone import TZ

from utils.data_manager import get_user_data, save_data


class ConfirmOnDutyView(discord.ui.View):

    def __init__(self, user_id: int):

        super().__init__(timeout=180)

        self.user_id = user_id
        self.confirmed = False

    @discord.ui.button(
        label="✅ Xác Nhận On-Duty",
        style=discord.ButtonStyle.success
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "❌ Đây không phải nút của bạn!",
                ephemeral=True
            )

            return

        self.confirmed = True

        embed = discord.Embed(
            title="✅ Đã Xác Nhận",
            description="Bạn vẫn đang ON-DUTY",
            color=0x00FF7F,
            timestamp=datetime.now(TZ)
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

        self.stop()

    async def on_timeout(self):

        if not self.confirmed:

            duty_data, user_id_str = get_user_data(self.user_id)

            if duty_data[user_id_str]['current_status'] == 'on-duty':

                current_session = duty_data[user_id_str]['current_session']

                start_time = datetime.fromisoformat(current_session['start_time'])

                end_time = datetime.now(TZ)

                duration = end_time - start_time

                duty_data[user_id_str]['history'].append({
                    'start_time': current_session['start_time'],
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration.total_seconds(),
                    'evidence_image': current_session.get('evidence_image'),
                    'discord_status': current_session.get('discord_status', 'Unknown')
                })

                duty_data[user_id_str]['current_status'] = 'off-duty'
                duty_data[user_id_str]['current_session'] = None

                save_data(duty_data)