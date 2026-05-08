from core.bot import bot
from core.config import TOKEN

# Events
import events.ready
import events.message
import events.voice

# Commands
import commands.duty.onduty
import commands.duty.offduty
import commands.duty.checkduty
import commands.duty.checkstats
import commands.duty.myduty
import commands.duty.dailystats

bot.run(TOKEN)