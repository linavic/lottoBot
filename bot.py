import logging
import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

# ייבוא פונקציות הזיכרון
from database_manager import get_user_data, update_user_data
# ייבוא שרת ה-keep_alive
from keep_alive import start_server

load_dotenv()

# הגדרות
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
PAYMENT_LINK = os.getenv('PAYMENT_LINK', 'https://www.paypal.com')

logging.basicConfig(level=logging.INFO)

if not API_TOKEN:
    logging.error("TELEGRAM_API_TOKEN is missing!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def generate_mock_predictions():
    """פונקציית גיבוי ליצירת מספרים אם הקובץ החיצוני לא נטען"""
    results = []
    for _ in range(10):
        nums = sorted(random.sample(range(1, 38), 6))
        strong = random.randint(1, 7)
        results.append(nums + [strong])
    return results

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    # יצירת רישום למשתמש בזיכרון
    await get_user_data(user_id)
    
    await message.reply(
        f"שלום {message.from_user.first_name}! 🎉\n"
        "ברוך הבא לבוט הלוטו הסטטיסטי.\n\n"
        "כמתנה, מגיעות לך **10 שורות ראשונות בחינם**.\n"
        "לחץ על הכפתור למטה כדי לקבל אותן.",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('🎰 קבל 10 שורות', callback_data='lotto')
        )
    )

@dp.callback_query_handler(lambda c: c.data == 'lotto')
async def process_lotto(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user = await get_user_data(user_id)
    
    # בדיקת מנוי או חינם
    if not user.get('has_used_free', False):
        # פעם ראשונה חינם
        try:
            from lotto_analysis import get_lotto_predictions
            results = get_lotto_predictions()
        except:
            results = generate_mock_predictions()
            
        await update_user_data(user_id, {"has_used_free": True})
        
        text = "🎫 **המספרים המומלצים שלך (חינם):**\n\n"
        for i, row in enumerate(results, 1):
            text += f"{i}. {' '.join(map(str, row[:-1]))} | חזק: {row[-1]}\n"
        
        await bot.send_message(user_id, text, parse_mode="Markdown")
        
    elif user.get('is_premium', False):
        # מנוי משלם
        try:
            from lotto_analysis import get_lotto_predictions
            results = get_lotto_predictions()
        except:
            results = generate_mock_predictions()
            
        text = "⭐ **תחזית VIP למנוי:**\n\n"
        for i, row in enumerate(results, 1):
            text += f"{i}. {' '.join(map(str, row[:-1]))} | חזק: {row[-1]}\n"
        
        await bot.send_message(user_id, text, parse_mode="Markdown")
        
    else:
        # חסימה והצעה למנוי
        await bot.send_message(
            user_id, 
            "🛑 **הגישה חסומה**\n\n"
            "כבר ניצלת את 10 השורות החינמיות שלך.\n"
            "כדי להמשיך לקבל תחזיות, הצטרף למנוי ב-10 ש\"ח לחודש.\n",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton('💳 לתשלום ב-PayPal', url=PAYMENT_LINK)
            )
        )

if __name__ == '__main__':
    if 'RENDER' in os.environ:
        from aiohttp import web
        server_app, port = start_server()
        loop = executor.get_event_loop()
        # הפעלת הבוט במקביל לשרת האינטרנט
        loop.create_task(executor.start_polling(dp, skip_updates=True))
        web.run_app(server_app, port=port)
    else:
        executor.start_polling(dp, skip_updates=True)
