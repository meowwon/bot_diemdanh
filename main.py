import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
import io
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo  


TZ = ZoneInfo("Asia/Ho_Chi_Minh") 
# now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = 'duty_data.json'
ACTIVITY_FILE = 'activity_logs.json'
EVIDENCE_DIR = Path('evidence_images')
EVIDENCE_DIR.mkdir(exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def migrate_old_data(data):
    migrated = {}
    for user_id, old_record in data.items():
        if 'history' in old_record:
            migrated[user_id] = old_record
        else:
            migrated[user_id] = {
                'username': old_record.get('username', 'Unknown'),
                'current_status': old_record.get('status', 'off-duty'),
                'current_session': None,
                'history': []
            }
            
            if old_record.get('status') == 'on-duty':
                migrated[user_id]['current_session'] = {
                    'start_time': old_record.get('start_time'),
                    'evidence_image': old_record.get('evidence_image'),
                    'discord_status': old_record.get('discord_status', 'Unknown')
                }
            elif old_record.get('status') == 'off-duty' and old_record.get('start_time') and old_record.get('end_time'):
                start = datetime.fromisoformat(old_record.get('start_time'))
                end = datetime.fromisoformat(old_record.get('end_time'))
                duration_secs = (end - start).total_seconds()
                
                migrated[user_id]['history'].append({
                    'start_time': old_record.get('start_time'),
                    'end_time': old_record.get('end_time'),
                    'duration_seconds': duration_secs,
                    'evidence_image': old_record.get('evidence_image'),
                    'discord_status': old_record.get('discord_status', 'Unknown')
                })
    
    return migrated

def get_user_data(user_id):
    duty_data = load_data()
    duty_data = migrate_old_data(duty_data)
    save_data(duty_data)
    
    user_id_str = str(user_id)
    if user_id_str not in duty_data:
        duty_data[user_id_str] = {
            'username': 'Unknown',
            'current_status': 'off-duty',
            'current_session': None,
            'history': []
        }
    
    return duty_data, user_id_str

def load_activity():
    if os.path.exists(ACTIVITY_FILE):
        with open(ACTIVITY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_activity(data):
    with open(ACTIVITY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_activity(user_id, activity_type, details=''):
    activity_data = load_activity()
    user_id_str = str(user_id)
    
    if user_id_str not in activity_data:
        activity_data[user_id_str] = []
    
    activity_data[user_id_str].append({
        'type': activity_type,
        'timestamp': datetime.now(TZ).isoformat(),
        'details': details
    })
    
    save_activity(activity_data)

def check_recent_activity(user_id, minutes=30):
    activity_data = load_activity()
    user_id_str = str(user_id)
    
    if user_id_str not in activity_data or not activity_data[user_id_str]:
        return False, 0
    
    now = datetime.now(TZ)
    recent_count = 0
    
    for activity in activity_data[user_id_str][-50:]:
        activity_time = datetime.fromisoformat(activity['timestamp'])
        diff_minutes = (now - activity_time).total_seconds() / 60
        
        if diff_minutes <= minutes:
            recent_count += 1
    
    return recent_count >= 3, recent_count
def is_playing_gta(member: discord.Member) -> bool:
    if not member.activities:
        return False

    for activity in member.activities:
        if isinstance(activity, discord.Game) or isinstance(activity, discord.Activity):
            if activity.name and "GTA5VN" in activity.name:
                return True

    return False
class ConfirmOnDutyView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)  # 3 phút timeout
        self.user_id = user_id
        self.confirmed = False
    
    @discord.ui.button(label="✅ Xác Nhận On-Duty", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.followup.send("❌ Đây không phải nút của bạn!", ephemeral=True)
            return
        
        self.confirmed = True
        embed = discord.Embed(
            title="✅ Đã Xác Nhận",
            description="Bạn đã xác nhận còn đang **ON-DUTY**!\nSẽ kiểm tra lại sau 3 tiếng nữa.",
            color=0x00FF7F,
            timestamp=datetime.now(TZ)
        )
        embed.set_footer(text="Hệ Thống Chấm Công Sở La Mesa")
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def on_timeout(self):
        if not self.confirmed:
            # Tự động off-duty
            duty_data, user_id_str = get_user_data(self.user_id)
            
            if duty_data[user_id_str]['current_status'] == 'on-duty':
                current_session = duty_data[user_id_str]['current_session']
                if current_session:
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
                    
                    user = bot.get_user(self.user_id)
                    if user:
                        try:
                            embed = discord.Embed(
                                title="⚠️ Tự Động Off-Duty",
                                description="Bạn đã bị **TỰ ĐỘNG OFF-DUTY** do không xác nhận trong 3 phút!",
                                color=0xFF0000,
                                timestamp=datetime.now(TZ)
                            )
                            hours = int(duration.total_seconds() // 3600)
                            minutes = int((duration.total_seconds() % 3600) // 60)
                            embed.add_field(name="⏱️ Tổng thời gian", value=f"```{hours}h {minutes}m```", inline=False)
                            embed.set_footer(text="Hệ Thống Chấm Công Sở La Mesa")
                            await user.send(embed=embed)
                        except:
                            pass

@tasks.loop(hours=3)
async def check_onduty_status():
    """Kiểm tra và nhắc nhở người dùng on-duty mỗi 1 tiếng"""
    duty_data = load_data()
    duty_data = migrate_old_data(duty_data)
    
    for user_id_str, data in duty_data.items():
        if data.get('current_status') == 'on-duty' and data.get('current_session'):
            user_id = int(user_id_str)
            user = bot.get_user(user_id)
            
            if user:
                try:
                    start_time = datetime.fromisoformat(data['current_session']['start_time'])
                    duration = datetime.now(TZ) - start_time
                    hours = int(duration.total_seconds() // 3600)
                    minutes = int((duration.total_seconds() % 3600) // 60)
                    
                    embed = discord.Embed(
                        title="🔔 Xác Nhận Trạng Thái On-Duty",
                        description=f"Bạn đang **ON-DUTY** được **{hours}h {minutes}m**\n\n⚠️ Vui lòng xác nhận bạn vẫn còn đang làm việc!\n**Nếu không xác nhận trong 3 phút, hệ thống sẽ tự động OFF-DUTY.**",
                        color=0xFFA500,
                        timestamp=datetime.now(TZ)
                    )
                    embed.add_field(name="⏰ Thời gian bắt đầu", value=f"```{start_time.strftime('%H:%M:%S - %d/%m/%Y')}```", inline=False)
                    embed.set_footer(text="Hệ Thống Chấm Công Sở La Mesa")
                    
                    view = ConfirmOnDutyView(user_id)
                    await user.send(embed=embed, view=view)
                except Exception as e:
                    print(f'❌ Không thể gửi DM cho user {user_id}: {e}')

@bot.event
async def on_ready():
    if bot.user:
        print(f'✅ Bot đã đăng nhập: {bot.user.name}')
    print(f'📊 Đang hoạt động trên {len(bot.guilds)} server(s)')
    try:
        # Xóa tất cả lệnh guild cũ, chỉ dùng global commands
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f'🗑️ Đã xóa lệnh guild cũ: {guild.name}')
        
        # Đồng bộ lại global commands
        synced = await bot.tree.sync()
        print(f'🔄 Đã đồng bộ {len(synced)} lệnh slash (global)')
        
        # Bắt đầu task kiểm tra on-duty
        if not check_onduty_status.is_running():
            check_onduty_status.start()
            print(f'🔔 Đã bắt đầu task kiểm tra on-duty mỗi 3 tiếng')
    except Exception as e:
        print(f'❌ Lỗi đồng bộ lệnh: {e}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    channel_name = message.channel.name if hasattr(message.channel, 'name') else 'DM'
    log_activity(message.author.id, 'message', f'Kênh: {channel_name}')
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        if after.channel:
            log_activity(member.id, 'voice_join', f'Tham gia: {after.channel.name}')
        elif before.channel:
            log_activity(member.id, 'voice_leave', f'Rời: {before.channel.name}')

@bot.tree.command(name="onduty", description="Chuyển sang trạng thái on-duty (cần hình ảnh bằng chứng)")
@app_commands.describe(image="Hình ảnh bằng chứng hoạt động Discord của bạn")
async def onduty(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer()
    
    if not image.content_type or not image.content_type.startswith('image/'):
        await interaction.followup.send("❌ Vui lòng upload một file hình ảnh hợp lệ!", ephemeral=True)
        return
    
    member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
    
    if member:
        status_map = {
        discord.Status.offline: "⚫ Offline",
        discord.Status.idle: "🟡 Idle/Away",
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.online: "🟢 Online"
    }

    if member.status != discord.Status.online:
        await interaction.followup.send(
            f"❌ Bạn cần đang ONLINE!\n📊 Hiện tại: {status_map.get(member.status)}",
            ephemeral=True
        )
        return

    if not is_playing_gta(member):
        await interaction.followup.send(
            "❌ Bạn phải đang chơi **GTA5VN** mới được on-duty!",
            ephemeral=True
        )
        return
    
    duty_data, user_id_str = get_user_data(interaction.user.id)
    
    if duty_data[user_id_str]['current_status'] == 'on-duty':
        await interaction.followup.send("❌ Bạn đã đang ở trạng thái on-duty rồi!", ephemeral=True)
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image.url) as resp:
                if resp.status == 200:
                    img_data = await resp.read()
                    img = Image.open(io.BytesIO(img_data))
                    
                    timestamp = datetime.now(TZ).strftime('%Y%m%d_%H%M%S')
                    filename = f"{interaction.user.id}_{timestamp}.png"
                    filepath = EVIDENCE_DIR / filename
                    img.save(filepath)
                    
                    status_text = str(member.status) if member else "Unknown"
                    
                    duty_data[user_id_str]['username'] = interaction.user.name
                    duty_data[user_id_str]['current_status'] = 'on-duty'
                    duty_data[user_id_str]['current_session'] = {
                        'start_time': datetime.now(TZ).isoformat(),
                        'evidence_image': str(filepath),
                        'discord_status': status_text
                    }
                    
                    save_data(duty_data)
                    log_activity(interaction.user.id, 'duty_on', f'Evidence: {filename}')
                    
                    start_time_display = datetime.now(TZ).strftime('%H:%M:%S - %d/%m/%Y')
                    
                    embed = discord.Embed(
                        title="",
                        description=f"# ✅ BẮT ĐẦU CÔNG VIỆC\n**{interaction.user.mention}** đã chuyển sang trạng thái **ON-DUTY**\n\n━━━━━━━━━━━━━━━━━━━━━",
                        color=0x00FF7F,
                        timestamp=datetime.now(TZ)
                    )
                    embed.add_field(name="⏰ Thời Gian Bắt Đầu", value=f"```{start_time_display}```", inline=False)
                    embed.add_field(name="📊 Trạng Thái Discord", value=f"```🟢 {status_text.capitalize()}```", inline=True)
                    embed.add_field(name="👤 Nhân Viên", value=f"```{interaction.user.name}```", inline=True)
                    embed.set_thumbnail(url=interaction.user.display_avatar.url)
                    embed.set_image(url=image.url)
                    embed.set_footer(text="LM | On-Duty System", icon_url=interaction.user.display_avatar.url)
                    embed.set_author(name="Hệ Thống Chấm Công Sở La Mesa", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
                    
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Không thể tải hình ảnh!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi xử lý hình ảnh: {str(e)}", ephemeral=True)

@bot.tree.command(name="offduty", description="Chuyển sang trạng thái off-duty")
async def offduty(interaction: discord.Interaction):
    duty_data, user_id_str = get_user_data(interaction.user.id)
    
    if duty_data[user_id_str]['current_status'] != 'on-duty':
        await interaction.followup.send("❌ Bạn không đang ở trạng thái on-duty!", ephemeral=True)
        return
    
    current_session = duty_data[user_id_str]['current_session']
    if not current_session:
        await interaction.followup.send("❌ Không tìm thấy session on-duty hiện tại!", ephemeral=True)
        return
    
    start_time = datetime.fromisoformat(current_session['start_time'])
    end_time = datetime.now(TZ)
    duration = end_time - start_time
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)
    
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
    log_activity(interaction.user.id, 'duty_off', f'Duration: {hours}h {minutes}m')
    
    end_time_display = end_time.strftime('%H:%M:%S - %d/%m/%Y')
    
    embed = discord.Embed(
        title="",
        description=f"# 🔴 KẾT THÚC CÔNG VIỆC\n**{interaction.user.mention}** đã chuyển sang trạng thái **OFF-DUTY**\n\n━━━━━━━━━━━━━━━━━━━━━",
        color=0xFF6347,
        timestamp=datetime.now(TZ)
    )
    embed.add_field(name="⏰ Thời Gian Kết Thúc", value=f"```{end_time_display}```", inline=False)
    embed.add_field(name="⏱️ Tổng Thời Gian On-Duty", value=f"```🕐 {hours} giờ {minutes} phút```", inline=False)
    embed.add_field(name="👤 Nhân Viên", value=f"```{interaction.user.name}```", inline=True)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="LM | On-Duty System", icon_url=interaction.user.display_avatar.url)
    embed.set_author(name="Hệ Thống Chấm Công Sở La Mesa", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="checkduty", description="Xem danh sách thành viên đang on-duty")
async def checkduty(interaction: discord.Interaction):
    duty_data = load_data()
    duty_data = migrate_old_data(duty_data)
    on_duty_members = []
    
    for user_id, data in duty_data.items():
        if data.get('current_status') == 'on-duty' and data.get('current_session'):
            start_time = datetime.fromisoformat(data['current_session']['start_time'])
            duration = datetime.now(TZ) - start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            
            on_duty_members.append({
                'user_id': user_id,
                'username': data.get('username', 'Unknown'),
                'duration': f"{hours}h {minutes}m",
                'discord_status': data['current_session'].get('discord_status', 'Unknown')
            })
    
    if not on_duty_members:
        await interaction.followup.send("📋 Hiện tại không có thành viên nào đang on-duty.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="",
        description=f"# 📋 DANH SÁCH ON-DUTY\nHiện tại có **{len(on_duty_members)}** thành viên đang làm việc\n\n━━━━━━━━━━━━━━━━━━━━━",
        color=0x4169E1,
        timestamp=datetime.now(TZ)
    )
    embed.set_footer(text="LM | Active Duty List", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
    embed.set_author(name="Hệ Thống Chấm Công Sở La Mesa")
    
    for idx, member in enumerate(on_duty_members, 1):
        status_emoji = "🟢" if "online" in member['discord_status'].lower() else "🟡"
        embed.add_field(
            name=f"#{idx} • {member['username']}",
            value=f"```⏱️ {member['duration']}\n{status_emoji} {member['discord_status'].capitalize()}```",
            inline=True
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="checkstats", description="Xem thống kê on-duty theo ngày/tuần/tháng/năm")
@app_commands.describe(
    ngay="Ngày (1-31, để trống nếu xem cả tháng)",
    thang="Tháng (1-12)",
    nam="Năm (ví dụ: 2025)",
    tuan="Tuần (1-53, để trống nếu không xem theo tuần)"
)
async def checkstats(
    interaction: discord.Interaction, 
    thang: int,
    nam: int,
    ngay: int | None = None,
    tuan: int | None = None
):
    duty_data = load_data()
    duty_data = migrate_old_data(duty_data)
    
    if ngay and (ngay < 1 or ngay > 31):
        await interaction.followup.send("❌ Ngày phải từ 1-31!", ephemeral=True)
        return
    
    if thang < 1 or thang > 12:
        await interaction.followup.send("❌ Tháng phải từ 1-12!", ephemeral=True)
        return
    
    if tuan and (tuan < 1 or tuan > 53):
        await interaction.followup.send("❌ Tuần phải từ 1-53!", ephemeral=True)
        return
    
    user_stats = {}
    
    for user_id, data in duty_data.items():
        user_stats[user_id] = {
            'username': data.get('username', 'Unknown'),
            'total_seconds': 0,
            'sessions': 0
        }
        
        for session in data.get('history', []):
            start_time = datetime.fromisoformat(session['start_time'])
            end_time = datetime.fromisoformat(session['end_time'])
            
            match = False
            if tuan:
                if start_time.isocalendar()[1] == tuan and start_time.year == nam:
                    match = True
            elif ngay:
                if start_time.day == ngay and start_time.month == thang and start_time.year == nam:
                    match = True
            else:
                if start_time.month == thang and start_time.year == nam:
                    match = True
            
            if match:
                duration = session.get('duration_seconds', 0)
                user_stats[user_id]['total_seconds'] += duration
                user_stats[user_id]['sessions'] += 1
        
        if data.get('current_status') == 'on-duty' and data.get('current_session'):
            current_start = datetime.fromisoformat(data['current_session']['start_time'])
            current_end = datetime.now(TZ)
            
            match = False
            if tuan:
                if current_start.isocalendar()[1] == tuan and current_start.year == nam:
                    match = True
            elif ngay:
                if current_start.day == ngay and current_start.month == thang and current_start.year == nam:
                    match = True
            else:
                if current_start.month == thang and current_start.year == nam:
                    match = True
            
            if match:
                duration = (current_end - current_start).total_seconds()
                user_stats[user_id]['total_seconds'] += duration
                user_stats[user_id]['sessions'] += 1
    
    user_stats = {k: v for k, v in user_stats.items() if v['sessions'] > 0}
    
    if not user_stats:
        if tuan:
            time_desc = f"tuần {tuan} năm {nam}"
        elif ngay:
            time_desc = f"ngày {ngay}/{thang}/{nam}"
        else:
            time_desc = f"tháng {thang}/{nam}"
        
        await interaction.followup.send(
            f"📊 Không có dữ liệu on-duty cho {time_desc}",
            ephemeral=True
        )
        return
    
    if tuan:
        title_time = f"Tuần {tuan} - Năm {nam}"
    elif ngay:
        title_time = f"Ngày {ngay}/{thang}/{nam}"
    else:
        title_time = f"Tháng {thang}/{nam}"
    
    embed = discord.Embed(
        title="",
        description=f"# 📊 THỐNG KÊ ON-DUTY\n📅 **{title_time}**\n🏆 Bảng xếp hạng thời gian làm việc\n\n━━━━━━━━━━━━━━━━━━━━━",
        color=0xFFD700,
        timestamp=datetime.now(TZ)
    )
    embed.set_footer(text="LM | Statistics Dashboard", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
    embed.set_author(name="Hệ Thống Chấm Công Sở La Mesa")
    
    sorted_stats = sorted(
        user_stats.items(),
        key=lambda x: x[1]['total_seconds'],
        reverse=True
    )
    
    for idx, (user_id, stats) in enumerate(sorted_stats, 1):
        hours = int(stats['total_seconds'] // 3600)
        minutes = int((stats['total_seconds'] % 3600) // 60)
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "📊"
        
        embed.add_field(
            name=f"{medal} #{idx} • {stats['username']}",
            value=f"```⏱️ {hours}h {minutes}m\n📈 {stats['sessions']} lần```",
            inline=True
        )
    
    await interaction.followup.send(embed=embed)
@bot.tree.command(name="myduty", description="Xem trạng thái duty của bạn")
async def myduty(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    duty_data, user_id_str = get_user_data(interaction.user.id)
    data = duty_data[user_id_str]

    now = datetime.now(TZ)

    def parse_time(ts: str):
        dt = datetime.fromisoformat(ts)
        return dt if dt.tzinfo else dt.replace(tzinfo=TZ)

    def format_duration(seconds: float):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"

    embed = discord.Embed(
        title="📋 THÔNG TIN DUTY CÁ NHÂN",
        color=0x00BFFF,
        timestamp=now
    )

    embed.add_field(name="👤 Người dùng", value=f"```{interaction.user.name}```", inline=True)
    embed.add_field(name="📊 Trạng thái", value=f"```{data['current_status'].upper()}```", inline=True)

    total_seconds = 0

    # 🟢 current session
    if data['current_status'] == 'on-duty' and data['current_session']:
        try:
            start_time = parse_time(data['current_session']['start_time'])
            duration = (now - start_time).total_seconds()

            embed.add_field(
                name="⏱️ Đang làm",
                value=f"```{format_duration(duration)}```",
                inline=False
            )
            embed.add_field(
                name="⏰ Bắt đầu",
                value=f"```{start_time.strftime('%H:%M:%S - %d/%m/%Y')}```",
                inline=False
            )

            total_seconds += duration
        except Exception:
            embed.add_field(name="⚠️ Lỗi dữ liệu", value="Không đọc được thời gian", inline=False)

    # 📊 history
    total_sessions = len(data.get('history', []))
    for session in data.get('history', []):
        total_seconds += session.get('duration_seconds', 0)

    embed.add_field(
        name="📈 Tổng thời gian",
        value=f"```{format_duration(total_seconds)}```",
        inline=True
    )

    embed.add_field(
        name="📊 Số lần on-duty",
        value=f"```{total_sessions} lần```",
        inline=True
    )

    embed.set_footer(text="LM | Personal Duty Stats")

    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="dailystats", description="Xem tổng thời gian on-duty hôm nay")
async def dailystats(interaction: discord.Interaction):
    duty_data = load_data()
    duty_data = migrate_old_data(duty_data)
    today = datetime.now(TZ).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    user_daily_stats = {}
    
    for user_id, data in duty_data.items():
        user_daily_stats[user_id] = {
            'username': data.get('username', 'Unknown'),
            'total_seconds': 0,
            'sessions': 0
        }
        
        for session in data.get('history', []):
            start_time = datetime.fromisoformat(session['start_time'])
            end_time = datetime.fromisoformat(session['end_time'])

            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=TZ)

            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=TZ)
            
            clamped_start = max(start_time, today_start)
            clamped_end = min(end_time, today_end)
            
            if clamped_start < clamped_end:
                duration_today = (clamped_end - clamped_start).total_seconds()
                user_daily_stats[user_id]['total_seconds'] += duration_today
                user_daily_stats[user_id]['sessions'] += 1
        
        if data.get('current_status') == 'on-duty' and data.get('current_session'):
            current_start = datetime.fromisoformat(data['current_session']['start_time'])
            current_end = datetime.now(TZ)
            
            clamped_start = max(current_start, today_start)
            clamped_end = min(current_end, today_end)
            
            if clamped_start < clamped_end:
                duration_today = (clamped_end - clamped_start).total_seconds()
                user_daily_stats[user_id]['total_seconds'] += duration_today
                user_daily_stats[user_id]['sessions'] += 1
    
    user_daily_stats = {k: v for k, v in user_daily_stats.items() if v['sessions'] > 0}
    
    if not user_daily_stats:
        await interaction.followup.send(
            f"📊 Chưa có ai on-duty trong ngày hôm nay ({today.strftime('%d/%m/%Y')})",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="",
        description=f"# 📊 THỐNG KÊ HÔM NAY\n📅 **{today.strftime('%d/%m/%Y')}**\n🏆 Bảng xếp hạng thời gian làm việc\n\n━━━━━━━━━━━━━━━━━━━━━",
        color=0xFFD700,
        timestamp=datetime.now(TZ)
    )
    embed.set_footer(text="LM | Daily Statistics", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
    embed.set_author(name="Hệ Thống Chấm Công Sở La Mesa")
    
    sorted_stats = sorted(
        user_daily_stats.items(),
        key=lambda x: x[1]['total_seconds'],
        reverse=True
    )
    
    for idx, (user_id, stats) in enumerate(sorted_stats, 1):
        hours = int(stats['total_seconds'] // 3600)
        minutes = int((stats['total_seconds'] % 3600) // 60)
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "📊"
        
        embed.add_field(
            name=f"{medal} #{idx} • {stats['username']}",
            value=f"```⏱️ {hours}h {minutes}m\n📈 {stats['sessions']} lần```",
            inline=True
        )
    
    await interaction.followup.send(embed=embed)

if __name__ == '__main__':
   
    bot.run("YOUR_BOT_TOKEN_HERE")
