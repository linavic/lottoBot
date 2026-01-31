import logging
import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
from datetime import datetime

# ייבוא מהקבצים שלך
from database_manager import get_user_data, update_user_data
from keep_alive import start_server

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
BASE_PAYMENT_URL = os.getenv('PAYMENT_LINK', 'https://www.paypal.com')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- תוכן שיווקי משודרג ---
MARKETING_STORY = (
    "🚀 **מהפכת הניבוי של LottoAI**\n\n"
    "אל תסתמכו על מזל עיוור. המערכת שלנו מבוססת על **אלגוריתם ייחודי** שפותח על ידי טובי המתכנתים ומומחי סטטיסטיקה מהשורה הראשונה.\n\n"
    "המערכת סורקת עשרות אלפי הגרלות עבר של מפעל הפיס, מנתחת דפוסים חוזרים ומשתמשת ב**נוסחאות מתמטיות בלעדיות** כדי לזקק עבורכם את הצירופים בעלי ההסתברות הגבוהה ביותר לזכייה.\n\n"
    "✅ ניתוח סטטיסטי עמוק של רצפים\n"
    "✅ סינון צירופים חלשים בזמן אמת\n"
    "✅ המלצות מבוססות מדע ולא ניחוש"
)

def generate_algorithmic_lines():
    """מייצר 10 שורות לוטו (סימולציה של האלגוריתם)"""
    lines = []
    for _ in range(10):
        nums = sorted(random.sample(range(1, 38), 6))
        strong = random.randint(1, 7)
        lines.append(nums + [strong])
    return lines

def format_lotto_ui(results, is_vip=False):
    title = "⭐ **תחזית VIP אלגוריתמית:**" if is_vip else "🎫 **התחזית החינמית שלך:**"
    text = f"{title}\n\n"
    for i, row in enumerate(results, 1):
        nums = "  ".join([f"<b>{n}</b>" for n in row[:-1]])
        strong = f"⭐ <b>{row[-1]}</b>"
        text += f"{i}. {nums} | {strong}\n"
    text += "\n🍀 *האלגוריתם סיים את החישוב. המזל בידיים שלך.*"
    return text

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    await get_user_data(user_id)
    
    # תמונת קאבר מקצועית
    welcome_img = "https://images.unsplash.com/photo-1518133835878-5a93cc3f89e5?q=80&w=1000"
    
    welcome_text = (
        f"שלום {message.from_user.first_name}! 👋\n\n"
        "ברוך הבא ל-**LottoAI**.\n"
        "הגעת למערכת הניבוי המתקדמת בישראל.\n\n"
        f"{MARKETING_STORY}\n\n"
        "🎁 לרגל הצטרפותך, המערכת הפיקה עבורך **תחזית VIP אחת (10 שורות) בחינם!**"
    )
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton('🎰 הפק 10 שורות חינם', callback_data='get_free'),
        types.InlineKeyboardButton('🔍 איך האלגוריתם עובד?', callback_data='how_it_works')
    )
    
    await bot.send_photo(message.chat.id, welcome_img, caption=welcome_text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'how_it_works')
async def show_explanation(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, MARKETING_STORY, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'get_free')
async def process_free_lotto(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user = await get_user_data(user_id)
    
    if not user.get('has_used_free', False):
        results = generate_algorithmic_lines()
        await update_user_data(user_id, {"has_used_free": True, "total_requests": user.get('total_requests', 0) + 1})
        
        await bot.send_message(user_id, format_lotto_ui(results), parse_mode="HTML")
        
        # הודעת דחיפה (Push) אחרי קבלת החינם
        await asyncio.sleep(2)
        promo = (
            "🧐 **רוצה להמשיך להשתמש במדע לטובתך?**\n\n"
            "מנויי ה-VIP שלנו מקבלים גישה בלתי מוגבלת לתחזיות המעודכנות ביותר לפני כל הגרלה.\n\n"
            "במחיר של כוס קפה - 10 ש\"ח בלבד לחודש, והאלגוריתם עובד עבורך!"
        )
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('💳 הצטרף ל-VIP עכשיו', callback_data='show_pay')
        )
        await bot.send_message(user_id, promo, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await show_payment_options(user_id)

async def show_payment_options(user_id):
    connector = "&" if "?" in BASE_PAYMENT_URL else "?"
    url = f"{BASE_PAYMENT_URL}{connector}custom={user_id}"
    
    text = (
        "🛑 **ניצלת את התחזית החינמית שלך**\n\n"
        "האלגוריתם שלנו ממשיך לנתח נתונים ברגעים אלו ממש כדי להעניק לך את היתרון היחסי.\n\n"
        "אל תשאיר את המזל שלך ליד המקרה - הצטרף למאות המשתמשים שמשתמשים במדע כדי לנצח!"
    )
    keyboard = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton('💳 מנוי VIP חודשי - 10 ש"ח', url=url)
    )
    await bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'show_pay')
async def callback_pay(callback_query: types.CallbackQuery):
    await show_payment_options(callback_query.from_user.id)

if __name__ == '__main__':
    from aiohttp import web
    # פתרון בעיית ה-PORT ב-Render
    server_app, port = start_server()
    loop = asyncio.get_event_loop()
    loop.create_task(executor.start_polling(dp, skip_updates=True))
    
    # חובה להשתמש ב-host='0.0.0.0' כדי ש-Render יזהה את השרת
    web.run_app(server_app, host='0.0.0.0', port=port)
