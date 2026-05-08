import discord
import aiohttp
import io

from discord import app_commands
from PIL import Image

from datetime import datetime

from core.bot import bot
from core.timezone import TZ
from core.config import EVIDENCE_DIR

from utils.data_manager import (
    get_user_data,
    save_data
)

from utils.activity_manager import log_activity

from utils.gta_checker import is_playing_gta


@bot.tree.command(
    name="onduty",
    description="On duty"
)
@app_commands.describe(
    image="Ảnh bằng chứng"
)
async def onduty(interaction: discord.Interaction, image: discord.Attachment):

    await interaction.response.defer()

    if not image.content_type.startswith('image/'):

        await interaction.followup.send(
            "❌ File không hợp lệ",
            ephemeral=True
        )

        return

    member = interaction.guild.get_member(interaction.user.id)

    if member.status != discord.Status.online:

        await interaction.followup.send(
            "❌ Bạn phải online",
            ephemeral=True
        )

        return

    if not is_playing_gta(member):

        await interaction.followup.send(
            "❌ Bạn phải chơi GTA5VN",
            ephemeral=True
        )

        return

    duty_data, user_id_str = get_user_data(interaction.user.id)

    if duty_data[user_id_str]['current_status'] == 'on-duty':

        await interaction.followup.send(
            "❌ Bạn đã on-duty",
            ephemeral=True
        )

        return

    async with aiohttp.ClientSession() as session:

        async with session.get(image.url) as resp:

            if resp.status == 200:

                img_data = await resp.read()

                img = Image.open(io.BytesIO(img_data))

                timestamp = datetime.now(TZ).strftime('%Y%m%d_%H%M%S')

                filename = f"{interaction.user.id}_{timestamp}.png"

                filepath = EVIDENCE_DIR / filename

                img.save(filepath)

                duty_data[user_id_str]['username'] = interaction.user.name

                duty_data[user_id_str]['current_status'] = 'on-duty'

                duty_data[user_id_str]['current_session'] = {
                    'start_time': datetime.now(TZ).isoformat(),
                    'evidence_image': str(filepath),
                    'discord_status': str(member.status)
                }

                save_data(duty_data)

                log_activity(
                    interaction.user.id,
                    'duty_on',
                    filename
                )

                await interaction.followup.send(
                    f"✅ {interaction.user.mention} đã ON-DUTY"
                )