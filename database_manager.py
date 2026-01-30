import os
import json

# לצורך השלב הראשון ועד שנחבר ענן סופי, נשתמש בקובץ מקומי.
# ברגע שתאשר שהבוט עונה, נחבר אותו ל-Cloud Storage האמיתי.
DB_FILE = "users_db.json"

async def get_user_data(user_id):
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({}, f)
    
    with open(DB_FILE, 'r') as f:
        data = json.load(f)
    
    if user_id not in data:
        data[user_id] = {
            "has_used_free": False,
            "is_premium": False,
            "subscription_expiry": None
        }
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)
            
    return data[user_id]

async def update_user_data(user_id, updates):
    with open(DB_FILE, 'r') as f:
        data = json.load(f)
    
    if user_id in data:
        data[user_id].update(updates)
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)
