import os
import json

DB_FILE = "users_db.json"

async def get_user_data(user_id):
    user_id = str(user_id)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({}, f)
    
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
    except:
        data = {}
    
    if user_id not in data:
        data[user_id] = {
            "has_used_free": False,
            "is_premium": False
        }
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)
            
    return data[user_id]

async def update_user_data(user_id, updates):
    user_id = str(user_id)
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
    except:
        data = {}
        
    if user_id not in data:
        data[user_id] = {"has_used_free": False, "is_premium": False}
        
    data[user_id].update(updates)
        
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)
