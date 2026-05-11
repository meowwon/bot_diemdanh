import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = 'data/duty_data.json'
ACTIVITY_FILE = 'data/activity_logs.json'

EVIDENCE_DIR = Path('evidence_images')
EVIDENCE_DIR.mkdir(exist_ok=True)