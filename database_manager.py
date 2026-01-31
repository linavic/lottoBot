import os
import json
from datetime import datetime, timedelta

DB_FILE = "users_db.json"

async def get_user_data(user_id):
    user_id = str(user_id)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
    
    if user_id not in data:
        data[user_id] = {
            "agreed_to_terms": False,
            "has_used_free": False,
            "is_premium": False,
            "expiry_date": None
        }
        save_db(data)
    return data[user_id]

async def user_agreed_to_terms(user_id):
    user_id = str(user_id)
    await update_user_data(user_id, {"agreed_to_terms": True})

async def update_user_data(user_id, updates):
    user_id = str(user_id)
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
    if user_id not in data:
        data[user_id] = {}
    data[user_id].update(updates)
    save_db(data)

async def set_user_premium(user_id, sub_id=None):
    expiry = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d %H:%M:%S")
    await update_user_data(user_id, {"is_premium": True, "expiry_date": expiry, "subscription_id": sub_id})
    return expiry

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
