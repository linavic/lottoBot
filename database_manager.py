import os
import json
from datetime import datetime, timedelta

# קובץ הזיכרון של המשתמשים
DB_FILE = "users_db.json"

async def get_user_data(user_id):
    """שליפת נתוני משתמש מהזיכרון עם תמיכה בנתוני שיווק ודחיפה"""
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
            "subscription_id": None,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_requests": 0
        }
        save_db(data)
            
    return data[user_id]

async def update_user_data(user_id, updates):
    """עדכון נתוני משתמש ושמירה מיידית"""
    user_id = str(user_id)
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
    
    if user_id in data:
        data[user_id].update(updates)
        save_db(data)

async def set_user_premium(user_id, sub_id=None):
    """הפיכת משתמש למנוי VIP ל-31 ימים"""
    expiry = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d %H:%M:%S")
    await update_user_data(user_id, {
        "is_premium": True,
        "expiry_date": expiry,
        "subscription_id": sub_id
    })
    return expiry

def save_db(data):
    """שמירת מסד הנתונים לקובץ JSON"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
