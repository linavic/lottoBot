import os
import json
from datetime import datetime, timedelta

# שם קובץ הזיכרון של המשתמשים
DB_FILE = "users_db.json"

async def get_user_data(user_id):
    """שליפת נתוני משתמש ושמירת תיעוד הצטרפות"""
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
            "agreement_date": None,
            "has_used_free": False,
            "is_premium": False,
            "expiry_date": None,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_db(data)
            
    return data[user_id]

async def user_agreed_to_terms(user_id):
    """תיעוד משפטי של הסכמת המשתמש לתנאי השימוש"""
    user_id = str(user_id)
    await update_user_data(user_id, {
        "agreed_to_terms": True,
        "agreement_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

async def update_user_data(user_id, updates):
    """עדכון נתוני משתמש בזיכרון"""
    user_id = str(user_id)
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
    
    if user_id in data:
        data[user_id].update(updates)
    else:
        data[user_id] = {
            "agreed_to_terms": False, 
            "has_used_free": False, 
            "is_premium": False,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data[user_id].update(updates)
        
    save_db(data)

async def set_user_premium(user_id, sub_id=None):
    """הפעלת מנוי VIP ל-31 ימים"""
    expiry = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d %H:%M:%S")
    await update_user_data(user_id, {
        "is_premium": True,
        "expiry_date": expiry,
        "subscription_id": sub_id
    })
    return expiry

def save_db(data):
    """שמירת הנתונים לקובץ JSON"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
