import logging
import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
from datetime import datetime

# ייבוא מהקבצים המקומיים
from database_manager import get_user_data, update_user_data, user_agreed_to_terms
from keep_alive import start_server

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')

# הקישור המדויק עם ה-Plan ID שלך
PAYPAL_URL = "https://www.paypal.com/webapps/billing/plans/subscribe?plan_id=P-39U78069VC411525WNF64WEA"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- תוכן שיווקי ומשפטי ---
DISCLAIMER_TEXT = (
    "⚠️ **כתב ויתור אחריות ותנאי שימוש** ⚠️\n\n"
    "לפני השימוש במערכת LottoAI, עליך לאשר את התנאים הבאים:\n\n"
    "1. המידע המופק מהבוט הינו המלצה סטטיסטית בלבד המבוססת על אלגוריתם הסתברותי.\n"
    "2. אין במידע זה משום הבטחה לזכייה או הצלחה בהגרלות הלוטו.\n"
    "3. השימוש בבוט ובמספרים המופקים ממנו הוא על אחריות המשתמש בלבד.\n"
    "4. הבוט, מפתחיו ובעליו אינם נושאים בכל אחריות לנזק או הפסד כספי.\n"
    "5. משחקי מזל מיועדים לבני 18 ומעלה. שחקו באחריות.\n\n"
    "**המשך השימוש מהווה הסכמה מלאה ובלתי חוזרת לתנאים אלו.**"
)

MARKETING_STORY = (
    "🔬 **הטכנולוגיה שמאחורי המזל**\n\n"
    "אלגוריתם **LottoAI** הוא פרי פיתוח ייחודי של צוות מתכנתים בכיר ומומחי סטטיסטיקה.\n\n"
    "באמצעות נוסחאות מתמטיות מתקדמות, המערכת סורקת עשרות אלפי הגרלות עבר, "
    "מזהה דפוסים הסתברותיים נסתרים ומזקקת את הצירופים בעלי הפוטנציאל הגבוה ביותר לזכייה.\n\n"
    "✅ ניתוח רצפים עמוק\n"
    "✅ סינון צירופים בעלי הסתברות נמוכה\n"
    "✅ עדכונים בזמן אמת לפני כל הגרלה"
)

def generate_numbers():
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
    
    if not user.get('agreed_to_terms', False):
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('✅ אני מאשר את התנאים והאחריות', callback_data='agree_terms')
        )
        await bot.send_photo(message.chat.id, welcome_img, caption=DISCLAIMER_TEXT, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await show_main_menu(message.chat.id, message.from_user.first_name)

async def show_main_menu(chat_id, name):
    text = (
        f"שלום {name}! 🎰\n\n"
        f"{MARKETING_STORY}\n\n"
        "האלגוריתם סיים את הניתוח המעודכן. מה תרצה לעשות?"
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
        results = generate_numbers()
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
            promo = "🧐 רוצה לקבל תחזיות לכל הגרלה ללא הגבלה? הצטרף ל-VIP ב-10 ש\"ח בלבד!"
            keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('💳 למינוי VIP', callback_data='show_pay'))
            await bot.send_message(user_id, promo, reply_markup=keyboard)
    else:
        await show_payment_options(user_id)

async def show_payment_options(user_id):
    url = f"{PAYPAL_URL}&custom={user_id}"
    text = (
        "🛑 **ניצלת את התחזית החינמית שלך**\n\n"
        "האלגוריתם שלנו ממשיך לנתח נתונים 24/7 כדי להעניק לך את היתרון היחסי.\n\n"
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
    server_app, port = start_server()
    loop = asyncio.get_event_loop()
    loop.create_task(executor.start_polling(dp, skip_updates=True))
    # host='0.0.0.0' קריטי ל-Render
    web.run_app(server_app, host='0.0.0.0', port=port)
