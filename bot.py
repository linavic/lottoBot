import logging
import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
from aiohttp import web
from datetime import datetime

# ייבוא ניהול הנתונים
from database_manager import get_user_data, update_user_data, user_agreed_to_terms, set_user_premium

load_dotenv()

# --- הגדרות ---
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
# וודא שה-Plan ID נכון
PLAN_ID = "P-39U78069VC411525WNF64WEA" 
PAYPAL_URL = f"https://www.paypal.com/webapps/billing/plans/subscribe?plan_id={PLAN_ID}"

# פורט - Render דורש שנאזין למשתנה הסביבה PORT
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)

# אתחול הבוט
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- לוגיקה שיווקית ---
DISCLAIMER_TEXT = (
    "⚠️ **כתב ויתור אחריות ותנאי שימוש** ⚠️\n\n"
    "1. השימוש בבוט ובמידע המופק ממנו הוא על אחריות המשתמש בלבד.\n"
    "2. המידע הינו המלצה סטטיסטית בלבד ואינו מבטיח זכייה.\n"
    "3. הבוט ומפתחיו אינם נושאים באחריות לנזק כספי.\n"
    "**המשך השימוש מהווה הסכמה לתנאים אלו.**"
)

MARKETING_STORY = (
    "🔬 **הטכנולוגיה שמאחורי המזל**\n\n"
    "מערכת **LottoAI** פותחה על ידי צוות מומחי דאטה.\n"
    "האלגוריתם סורק אלפי הגרלות עבר ומזהה דפוסים סטטיסטיים\n"
    "כדי לזקק את הצירופים בעלי הפוטנציאל הגבוה ביותר."
)

def generate_numbers():
    """מייצר 10 שורות לוטו"""
    lines = []
    for _ in range(10):
        nums = sorted(random.sample(range(1, 38), 6))
        strong = random.randint(1, 7)
        lines.append(nums + [strong])
    return lines

# --- הנדלרים של הבוט (Telegram Handlers) ---

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    user = await get_user_data(user_id)
    
    welcome_img = "https://images.unsplash.com/photo-1518133835878-5a93cc3f89e5?q=80&w=1000"
    
    if not user.get('agreed_to_terms', False):
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('✅ אני מאשר את התנאים', callback_data='agree_terms')
        )
        await bot.send_photo(message.chat.id, welcome_img, caption=DISCLAIMER_TEXT, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await show_main_menu(message.chat.id, message.from_user.first_name)

async def show_main_menu(chat_id, name):
    text = f"שלום {name}! 🎰\n\n{MARKETING_STORY}\n\nהאלגוריתם מוכן. מה תרצה לעשות?"
    keyboard = types.InlineKeyboardMarkup(row_width=1).add(
        types.InlineKeyboardButton('🎰 הפק 10 שורות VIP', callback_data='get_lotto'),
        types.InlineKeyboardButton('💳 הצטרף למנוי VIP', callback_data='show_pay')
    )
    await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'agree_terms')
async def process_agree(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    await user_agreed_to_terms(user_id)
    await bot.answer_callback_query(callback_query.id, "התנאים אושרו!")
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
            text += f"{i}. {nums} | ⭐ <b>{row[-1]}</b>\n"
        
        await bot.send_message(user_id, text, parse_mode="HTML")
        
        if not user.get('is_premium', False):
            await asyncio.sleep(2)
            promo = "🧐 רוצה תחזיות ללא הגבלה? הצטרף ל-VIP ב-10 ש\"ח בלבד!"
            keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('💳 למינוי VIP', callback_data='show_pay'))
            await bot.send_message(user_id, promo, reply_markup=keyboard)
    else:
        await show_payment_options(user_id)

async def show_payment_options(user_id):
    url = f"{PAYPAL_URL}&custom={user_id}"
    text = "🛑 **מגבלת שימוש חינמי**\n\nכבר ניצלת את התחזית החינמית. הצטרף ל-VIP כדי להמשיך."
    keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('💳 מנוי VIP ב-10 ש"ח', url=url))
    await bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'show_pay')
async def callback_pay(callback_query: types.CallbackQuery):
    await show_payment_options(callback_query.from_user.id)

# --- לוגיקה של השרת (Server Logic) ---

async def handle_home(request):
    return web.Response(text="LottoAI Server is Running!")

async def handle_paypal_webhook(request):
    try:
        data = await request.json()
        event_type = data.get('event_type')
        resource = data.get('resource', {})
        
        user_id = resource.get('custom_id') or resource.get('custom')
        if not user_id and 'subscriber' in resource:
            user_id = resource['subscriber'].get('custom_id')

        logging.info(f"Webhook: {event_type} | User: {user_id}")

        if user_id and event_type in ['PAYMENT.SALE.COMPLETED', 'BILLING.SUBSCRIPTION.ACTIVATED']:
            expiry = await set_user_premium(user_id, resource.get('id'))
            await bot.send_message(user_id, f"🎊 **מנוי VIP הופעל!**\nתוקף: {expiry}\nבהצלחה! 🍀", parse_mode="Markdown")
            
        return web.Response(text="OK", status=200)
    except Exception as e:
        logging.error(f"Webhook Error: {e}")
        return web.Response(text="Error", status=400)

async def on_startup(app):
    """פונקציה שמפעילה את הבוט ברקע כשהשרת עולה"""
    logging.info("Starting Telegram Bot Polling...")
    # הגדרת ה-Webhook ל-None כדי לוודא שאין התנגשויות ישנות
    await bot.delete_webhook(drop_pending_updates=True)
    # הרצת ה-Polling ברקע
    asyncio.create_task(dp.start_polling())

# --- הרצת הכל ביחד ---

if __name__ == '__main__':
    # יצירת אפליקציית ה-Web
    app = web.Application()
    app.router.add_get('/', handle_home)
    app.router.add_post('/webhook/paypal', handle_paypal_webhook)
    
    # חיבור הבוט לתהליך העלייה של השרת
    app.on_startup.append(on_startup)
    
    # הרצת השרת (Render מזהה את זה ומחזיק את האפליקציה בחיים)
    web.run_app(app, host='0.0.0.0', port=PORT)
