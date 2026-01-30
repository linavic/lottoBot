import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

# ייבוא פונקציות הזיכרון והשרת מהקבצים שלך
from database_manager import get_user_data, update_user_data
from keep_alive import start_server

load_dotenv()

# הגדרות (חובה שיופיעו ב-Environment Variables ב-Render)
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
PAYMENT_LINK = os.getenv('PAYMENT_LINK', 'https://www.paypal.com')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# פונקציה פשוטה ליצירת מספרים (כדי שלא נהיה תלויים בקבצים חיצוניים כרגע)
def get_mock_numbers():
    import random
    lines = []
    for _ in range(10):
        nums = sorted(random.sample(range(1, 38), 6))
        strong = random.randint(1, 7)
        lines.append(f"{' '.join(map(str, nums))} | חזק: {strong}")
    return "\n".join(lines)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    await get_user_data(user_id) # רישום המשתמש בזיכרון
    
    await message.reply(
        f"שלום {message.from_user.first_name}! 🎉\n"
        "ברוך הבא לבוט הלוטו הסטטיסטי.\n\n"
        "כמתנה, מגיעה לך **תחזית אחת של 10 שורות בחינם**.\n"
        "לחץ על הכפתור למטה כדי לקבל אותן.",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('🎰 קבל 10 שורות', callback_data='lotto')
        )
    )

@dp.callback_query_handler(lambda c: c.data == 'lotto')
async def process_lotto(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user = await get_user_data(user_id)
    
    # אם המשתמש הוא אדמין (אתה), הוא תמיד יכול לקבל מספרים
    is_admin = str(user_id) == os.getenv('ADMIN_ID')
    
    if not user.get('has_used_free', False) or user.get('is_premium', False) or is_admin:
        # הפקה של מספרים
        results = get_mock_numbers()
        
        # אם זה שימוש חינמי - נסמן אותו
        if not user.get('has_used_free', False) and not is_admin:
            await update_user_data(user_id, {"has_used_free": True})
        
        await bot.send_message(user_id, f"🎫 **המספרים המומלצים עבורך:**\n\n{results}")
    else:
        # חסימה והצעה למנוי
        await bot.send_message(
            user_id, 
            "🛑 **הגישה חסומה**\n\n"
            "כבר ניצלת את התחזית החינמית שלך.\n"
            "כדי להמשיך לקבל תחזיות ללא הגבלה, הצטרף למנוי ב-10 ש\"ח לחודש.\n",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton('💳 לתשלום ב-PayPal', url=PAYMENT_LINK)
            )
        )

if __name__ == '__main__':
    from aiohttp import web
    # הפעלת שרת keep_alive כדי ש-Render לא יכבה את הבוט
    server_app, port = start_server()
    
    loop = asyncio.get_event_loop()
    # הרצת הבוט ברקע
    loop.create_task(executor.start_polling(dp, skip_updates=True))
    
    # הרצת השרת (חוסם)
    web.run_app(server_app, port=port)
