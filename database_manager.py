import os
import json
from datetime import datetime, timedelta

# קובץ הזיכרון של המשתמשים
DB_FILE = "users_db.json"

async def get_user_data(user_id):
    """שליפת נתוני משתמש מהזיכרון"""
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
            "has_used_free": False,
            "is_premium": False,
            "expiry_date": None,
            "subscription_id": None
        }
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
            
    return data[user_id]

async def update_user_data(user_id, updates):
    """עדכון נתוני משתמש ספציפיים"""
    user_id = str(user_id)
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
        
    if user_id not in data:
        data[user_id] = {"has_used_free": False, "is_premium": False, "expiry_date": None}
        
    data[user_id].update(updates)
        
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def set_user_premium(user_id, sub_id=None, months=1):
    """הפיכת משתמש לפרימיום עם תאריך תפוגה"""
    user_id = str(user_id)
    # חישוב תאריך תפוגה (31 יום קדימה)
    expiry = datetime.now() + timedelta(days=31 * months)
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S")
    
    await update_user_data(user_id, {
        "is_premium": True,
        "expiry_date": expiry_str,
        "subscription_id": sub_id
    })
    return expiry_str
