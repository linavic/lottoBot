import logging
import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
from datetime import datetime

from database_manager import get_user_data, update_user_data
from keep_alive import start_server

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
# לינק המנוי שיצרת בפייפאל (ללא ה-custom_id)
BASE_PAYMENT_URL = os.getenv('PAYMENT_LINK', 'https://www.paypal.com/billing/subscriptions/subscribe?plan_id=YOUR_PLAN_ID')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def generate_lotto_lines():
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
    await get_user_data(user_id)
    
    await message.reply(
        f"שלום {message.from_user.first_name}! 🎰\n"
        "ברוך הבא לבוט הלוטו הסטטיסטי.\n\n"
        "מגיעה לך <b>תחזית אחת של 10 שורות בחינם</b>.\n"
        "לחץ על הכפתור למטה כדי לקבל אותן.",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('🎰 קבל 10 שורות', callback_data='lotto')
        )
    )

@dp.callback_query_handler(lambda c: c.data == 'lotto')
async def process_lotto(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user = await get_user_data(user_id)
    
    # בדיקת מנוי פרימיום ותוקף
    is_premium = user.get('is_premium', False)
    if is_premium and user.get('expiry_date'):
        expiry = datetime.strptime(user['expiry_date'], "%Y-%m-%d %H:%M:%S")
        if expiry < datetime.now():
            is_premium = False
            await update_user_data(user_id, {"is_premium": False})

    if not user.get('has_used_free', False) or is_premium:
        results = generate_lotto_lines()
        
        # סימון שימוש בחינם
        if not is_premium:
            await update_user_data(user_id, {"has_used_free": True})
        
        title = "⭐ תחזית VIP למנוי פעיל:" if is_premium else "🎫 המספרים שלך (מתנת הצטרפות):"
        await bot.send_message(user_id, f"<b>{title}</b>\n\n{results}", parse_mode="HTML")
        
    else:
        # חסימה והצעה למנוי עם custom_id בשביל ה-Webhook
        # אנחנו מוסיפים &custom=USER_ID לסוף הלינק של פייפאל
        connector = "&" if "?" in BASE_PAYMENT_URL else "?"
        personal_pay_url = f"{BASE_PAYMENT_URL}{connector}custom={user_id}"
        
        await bot.send_message(
            user_id, 
            "🛑 <b>הגישה חסומה</b>\n\n"
            "כבר ניצלת את 10 השורות החינמיות שלך.\n"
            "כדי להמשיך לקבל תחזיות ללא הגבלה, הצטרף למנוי ה-VIP ב-10 ש\"ח לחודש.\n",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton('💳 הרשמה למנוי ב-PayPal', url=personal_pay_url)
            )
        )

if __name__ == '__main__':
    if 'RENDER' in os.environ:
        from aiohttp import web
        server_app, port = start_server()
        loop = asyncio.get_event_loop()
        loop.create_task(executor.start_polling(dp, skip_updates=True))
        web.run_app(server_app, port=port)
    else:
        executor.start_polling(dp, skip_updates=True)
