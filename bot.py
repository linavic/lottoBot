import logging
import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
from datetime import datetime

# ייבוא מהקבצים שלך
from database_manager import get_user_data, update_user_data, user_agreed_to_terms
from keep_alive import start_server

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
BASE_PAYMENT_URL = os.getenv('PAYMENT_LINK', 'https://www.paypal.com')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- תוכן שיווקי ומשפטי ---
DISCLAIMER_TEXT = (
    "⚠️ **כתב ויתור אחריות ותנאי שימוש** ⚠️\n\n"
    "1. השימוש בבוט זה ובמידע המופק ממנו הוא על אחריות המשתמש בלבד.\n"
    "2. המידע המופק מהאלגוריתם הינו בגדר המלצה סטטיסטית בלבד ואינו מבטיח זכייה.\n"
    "3. הבוט, מפתחיו וכל גורם הקשור אליו אינם נושאים בכל אחריות (ישירה או עקיפה) "
    "לכל נזק, הפסד כספי או אכזבה העלולים להיגרם מהשימוש בבוט.\n"
    "4. מפעלי הלוטו הינם משחקי מזל. אנו ממליצים לשחק באחריות ובתקציב מוגדר מראש.\n\n"
    "**המשך השימוש בבוט מהווה הסכמה מלאה ובלתי חוזרת לתנאים אלו.**"
)

MARKETING_STORY = (
    "🔬 **הטכנולוגיה שמאחורי המזל**\n\n"
    "מערכת **LottoAI** פותחה על ידי צוות של טובי המתכנתים ומומחי סטטיסטיקה.\n"
    "האלגוריתם הייחודי שלנו סורק עשרות אלפי הגרלות עבר, מנתח דפוסים ומשתמש "
    "בנוסחאות מתמטיות מתקדמות כדי לזקק את הצירופים בעלי הפוטנציאל הגבוה ביותר."
)

def generate_algorithmic_lines():
    lines = []
    for _ in range(10):
        nums = sorted(random.sample(range(1, 38), 6))
        strong = random.randint(1, 7)
        lines.append(nums + [strong])
    return lines

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    user = await get_user_data(user_id)
    
    welcome_img = "https://images.unsplash.com/photo-1518133835878-5a93cc3f89e5?q=80&w=1000"
    
    # בדיקה: האם המשתמש כבר אישר את התנאים?
    if not user.get('agreed_to_terms', False):
        text = (
            f"שלום {message.from_user.first_name}! 👋\n\n"
            "ברוך הבא ל-**LottoAI**.\n"
            "לפני שנתחיל להשתמש בכוח של האלגוריתם, עליך לקרוא ולאשר את תנאי השימוש:\n\n"
            f"{DISCLAIMER_TEXT}"
        )
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('✅ אני מאשר את התנאים', callback_data='agree_terms')
        )
        await bot.send_photo(message.chat.id, welcome_img, caption=text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        # אם כבר אישר - שלח לו את הודעת הברוך הבא השיווקית
        await show_main_menu(message.chat.id, message.from_user.first_name)

async def show_main_menu(chat_id, name):
    text = (
        f"שלום {name}! שמחים שחזרת. 🎰\n\n"
        f"{MARKETING_STORY}\n\n"
        "האלגוריתם מוכן לעבודה. מה תרצה לעשות?"
    )
    keyboard = types.InlineKeyboardMarkup(row_width=1).add(
        types.InlineKeyboardButton('🎰 הפק 10 שורות VIP', callback_data='get_lotto'),
        types.InlineKeyboardButton('💳 הצטרף למנוי VIP', callback_data='show_pay')
    )
    await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'agree_terms')
async def process_agree(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    await user_agreed_to_terms(user_id)
    await bot.answer_callback_query(callback_query.id, "התנאים אושרו בהצלחה!")
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await show_main_menu(callback_query.message.chat.id, callback_query.from_user.first_name)

@dp.callback_query_handler(lambda c: c.data == 'get_lotto')
async def process_lotto(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user = await get_user_data(user_id)
    
    if not user.get('has_used_free', False) or user.get('is_premium', False):
        results = generate_algorithmic_lines()
        
        # עדכון שימוש חינם אם רלוונטי
        if not user.get('is_premium', False):
            await update_user_data(user_id, {"has_used_free": True})
        
        text = "🎰 **התחזית האלגוריתמית עבורך:**\n\n"
        for i, row in enumerate(results, 1):
            nums = "  ".join([f"<b>{n}</b>" for n in row[:-1]])
            strong = f"⭐ <b>{row[-1]}</b>"
            text += f"{i}. {nums} | {strong}\n"
        
        await bot.send_message(user_id, text, parse_mode="HTML")
        
        if not user.get('is_premium', False):
            await asyncio.sleep(2)
            promo = "🧐 רוצה לקבל תחזיות ללא הגבלה בכל הגרלה? הצטרף ל-VIP ב-10 ש\"ח בלבד!"
            keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('💳 למינוי VIP', callback_data='show_pay'))
            await bot.send_message(user_id, promo, reply_markup=keyboard)
    else:
        await show_payment_options(user_id)

async def show_payment_options(user_id):
    connector = "&" if "?" in BASE_PAYMENT_URL else "?"
    url = f"{BASE_PAYMENT_URL}{connector}custom={user_id}"
    text = "🛑 **מגבלת שימוש חינמי**\n\nכבר ניצלת את התחזית החינמית שלך. הצטרף למנוי ה-VIP כדי להמשיך."
    keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('💳 מנוי VIP ב-10 ש"ח', url=url))
    await bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'show_pay')
async def callback_pay(callback_query: types.CallbackQuery):
    await show_payment_options(callback_query.from_user.id)

if __name__ == '__main__':
    from aiohttp import web
    server_app, port = start_server()
    loop = asyncio.get_event_loop()
    loop.create_task(executor.start_polling(dp, skip_updates=True))
    # host='0.0.0.0' פותר את בעיית ה-Port ב-Render
    web.run_app(server_app, host='0.0.0.0', port=port)
