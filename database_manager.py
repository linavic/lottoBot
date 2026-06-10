import os
import json
from datetime import datetime, timedelta

DB_FILE = "users_db.json"

DEFAULT_USER = {
    "agreed_to_terms": False,
    "has_used_free": False,
    "is_premium": False,
    "expiry_date": None,
    "subscription_id": None,
    "free_credits": 0,
    "referred_by": None,
    "referral_awarded": False
}

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
        data[user_id] = DEFAULT_USER.copy()
        save_db(data)
    else:
        missing_defaults = False
        for key, value in DEFAULT_USER.items():
            if key not in data[user_id]:
                data[user_id][key] = value
                missing_defaults = True
        if missing_defaults:
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

async def set_referrer(user_id, referrer_id):
    user_id = str(user_id)
    referrer_id = str(referrer_id)
    if user_id == referrer_id:
        return False

    user = await get_user_data(user_id)
    if user.get("referred_by"):
        return False

    await update_user_data(user_id, {"referred_by": referrer_id})
    return True

async def award_referral_credit(user_id):
    user_id = str(user_id)
    user = await get_user_data(user_id)
    referrer_id = user.get("referred_by")
    if not referrer_id or user.get("referral_awarded"):
        return None

    referrer = await get_user_data(referrer_id)
    credits = int(referrer.get("free_credits", 0) or 0) + 1
    await update_user_data(referrer_id, {"free_credits": credits})
    await update_user_data(user_id, {"referral_awarded": True})
    return referrer_id

async def use_free_credit(user_id):
    user_id = str(user_id)
    user = await get_user_data(user_id)
    credits = int(user.get("free_credits", 0) or 0)
    if credits <= 0:
        return False

    await update_user_data(user_id, {"free_credits": credits - 1})
    return True

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
