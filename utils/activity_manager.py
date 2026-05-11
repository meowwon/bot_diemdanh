import os
import json
from datetime import datetime

from core.config import ACTIVITY_FILE
from core.timezone import TZ


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

    if user_id_str not in activity_data:
        return False, 0

    now = datetime.now(TZ)

    recent_count = 0

    for activity in activity_data[user_id_str][-50:]:

        activity_time = datetime.fromisoformat(activity['timestamp'])

        diff_minutes = (now - activity_time).total_seconds() / 60

        if diff_minutes <= minutes:
            recent_count += 1

    return recent_count >= 3, recent_count