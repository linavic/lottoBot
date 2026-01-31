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

# --- טקסטים שיווקיים ---
ABOUT_TEXT = (
    "🤖 **הטכנולוגיה שמאחורי המזל שלך**\n\n"
    "האלגוריתם שלנו אינו מבוסס על ניחושים. צוות של מתכנתים בכירים ומומחי סטטיסטיקה "
    "ניתחו עשרות אלפי הגרלות עבר של הלוטו הישראלי.\n\n"
    "✅ **ניתוח דפוסים (Pattern Recognition)**\n"
    "✅ **חישוב הסתברויות מתקדם**\n"
    "✅ **סינון רצפים בעלי סבירות נמוכה**\n\n"
    "באמצעות נוסחאות ייחודיות, אנחנו מזקקים עבורך את הצירופים בעלי הפוטנציאל הגבוה ביותר לזכייה בהגרלה הקרובה."
)

def format_lotto_results(results):
    text = "🎰 **התחזית האלגוריתמית שלך:**\n\n"
    for i, row in enumerate(results, 1):
        nums = "  ".join([f"<b>{n}</b>" for n in row[:-1]])
        strong = f"⭐ <b>{row[-1]}</b>"
        text += f"{i}. {nums} | {strong}\n"
    text += "\n🍀 *זכור: הסטטיסטיקה לצידך, אבל המזל הוא הקובע הסופי.*"
    return text

def generate_numbers():
    """מייצר 10 שורות לוטו (כאן יבוא האלגוריתם האמיתי שלך)"""
    lines = []
    for _ in range(10):
        nums = sorted(random.sample(range(1, 38), 6))
        strong = random.randint(1, 7)
        lines.append(nums + [strong])
    return lines

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    await get_user_data(user_id)
    
    # תמונת ברוכים הבאים (Placeholder)
    welcome_img = "https://images.unsplash.com/photo-1518133835878-5a93cc3f89e5?q=80&w=1000" 
    
    text = (
        f"שלום {message.from_user.first_name}! 👋\n\n"
        "ברוך הבא ל-**LottoAI** - הבוט היחיד בישראל שמשלב בינה מלאכותית וסטטיסטיקה מתקדמת לניחוש תוצאות הלוטו.\n\n"
        f"{ABOUT_TEXT}\n\n"
        "🎁 כמתנת הצטרפות, הכנו עבורך **תחזית VIP אחת (10 שורות) בחינם לחלוטין!**"
    )
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton('🎰 קבל 10 שורות בחינם', callback_data='lotto_free'),
        types.InlineKeyboardButton('📊 איך זה עובד?', callback_data='how_it_works')
    )
    
    await bot.send_photo(message.chat.id, welcome_img, caption=text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'how_it_works')
async def how_it_works(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, ABOUT_TEXT, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'lotto_free')
async def process_free_lotto(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user = await get_user_data(user_id)
    
    if not user.get('has_used_free', False):
        results = generate_numbers()
        await update_user_data(user_id, {"has_used_free": True})
        
        await bot.send_message(user_id, format_lotto_results(results), parse_mode="HTML")
        
        # הודעת דחיפה למנוי אחרי שקיבל חינם
        promo_text = (
            "🧐 **רוצה להגדיל את הסיכויים שלך בכל הגרלה?**\n\n"
            "מנויי ה-VIP שלנו מקבלים תחזיות מעודכנות לכל הגרלה, "
            "כולל ניתוח חם/קר של מספרים וגישה לצירופים הסודיים של האלגוריתם.\n\n"
            "במחיר של כוס קפה - 10 ש\"ח בלבד לחודש!"
        )
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('💳 הצטרף ל-VIP עכשיו', callback_data='show_pay')
        )
        await asyncio.sleep(2) # השהייה קטנה ליצירת עניין
        await bot.send_message(user_id, promo_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await show_payment_options(user_id)

async def show_payment_options(user_id):
    connector = "&" if "?" in BASE_PAYMENT_URL else "?"
    url = f"{BASE_PAYMENT_URL}{connector}custom={user_id}"
    
    text = (
        "🛑 **מגבלת שימוש חינמי**\n\n"
        "ניצלת את התחזית החינמית שלך.\n"
        "האלגוריתם ממשיך לעבוד ולנתח נתונים ברגעים אלו ממש!\n\n"
        "הצטרף למאות המשתמשים שכבר משתמשים במדע כדי לנצח את המזל."
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
    server_app, port = start_server()
    loop = asyncio.get_event_loop()
    loop.create_task(executor.start_polling(dp, skip_updates=True))
    web.run_app(server_app, port=port)
