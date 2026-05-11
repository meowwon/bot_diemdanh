import os
import json
from datetime import datetime

from core.config import DATA_FILE

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

            elif old_record.get('status') == 'off-duty':
                if old_record.get('start_time') and old_record.get('end_time'):

                    start = datetime.fromisoformat(old_record['start_time'])
                    end = datetime.fromisoformat(old_record['end_time'])

                    migrated[user_id]['history'].append({
                        'start_time': old_record['start_time'],
                        'end_time': old_record['end_time'],
                        'duration_seconds': (end - start).total_seconds(),
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