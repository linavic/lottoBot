import logging
import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

# ייבוא מהקבצים שלך
from database_manager import get_user_data, update_user_data
from keep_alive import start_server

load_dotenv()

# הגדרות טוקן
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
PAYMENT_LINK = os.getenv('PAYMENT_LINK', 'https://www.paypal.com')

logging.basicConfig(level=logging.INFO)

if not API_TOKEN:
    logging.error("Missing TELEGRAM_API_TOKEN in Environment Variables!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def get_numbers():
    """מייצר 10 שורות לוטו רנדומליות"""
    lines = []
    for _ in range(10):
        nums = sorted(random.sample(range(1, 38), 6))
        strong = random.randint(1, 7)
        lines.append(f"{' '.join(map(str, nums))} | חזק: {strong}")
    return "\n".join(lines)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    await get_user_data(user_id) # רישום ראשוני
    
    await message.reply(
        f"שלום {message.from_user.first_name}! 🎉\n"
        "ברוך הבא לבוט הלוטו הסטטיסטי.\n\n"
        "מגיעה לך **תחזית אחת של 10 שורות בחינם**.\n"
        "לחץ על הכפתור למטה כדי לקבל אותן.",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('🎰 קבל 10 שורות', callback_data='lotto')
        )
    )

@dp.callback_query_handler(lambda c: c.data == 'lotto')
async def process_lotto(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user = await get_user_data(user_id)
    
    # בדיקה: האם הוא כבר קיבל חינם?
    if not user.get('has_used_free', False):
        results = get_numbers()
        await update_user_data(user_id, {"has_used_free": True})
        
        await bot.send_message(
            user_id, 
            f"🎫 **המספרים המומלצים שלך (חינם):**\n\n{results}"
        )
        
    elif user.get('is_premium', False):
        results = get_numbers()
        await bot.send_message(
            user_id, 
            f"⭐ **תחזית VIP למנוי פעיל:**\n\n{results}"
        )
        
    else:
        # חסימה והצעה למנוי
        await bot.send_message(
            user_id, 
            "🛑 **הגישה חסומה**\n\n"
            "כבר השתמשת ב-10 השורות החינמיות שלך.\n"
            "כדי להמשיך לקבל תחזיות, הצטרף למנוי ב-10 ש\"ח בלבד.\n",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton('💳 לתשלום ב-PayPal', url=PAYMENT_LINK)
            )
        )

if __name__ == '__main__':
    if 'RENDER' in os.environ:
        from aiohttp import web
        # הרצת שרת keep_alive במקביל לבוט
        server_app, port = start_server()
        loop = asyncio.get_event_loop()
        loop.create_task(executor.start_polling(dp, skip_updates=True))
        web.run_app(server_app, port=port)
    else:
        executor.start_polling(dp, skip_updates=True)
