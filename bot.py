import logging
import os
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# ייבוא לוגיקת לוטו
from lotto_analysis import get_lotto_predictions
from keep_alive import start_server

load_dotenv()

# הגדרות סביבה
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL') # Render PostgreSQL URL
PAYPAL_SUB_LINK = os.getenv('PAYPAL_SUB_LINK') # לינק לתוכנית מנוי בפייפאל

logging.basicConfig(level=logging.INFO)

# הגדרת בסיס הנתונים (SQL)
Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True)
    has_used_free = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    subscription_id = Column(String, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

# יצירת טבלאות אם לא קיימות
Base.metadata.create_all(engine)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

def get_or_create_user(user_id):
    user = session.query(User).filter_by(user_id=str(user_id)).first()
    if not user:
        user = User(user_id=str(user_id))
        session.add(user)
        session.commit()
    return user

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    get_or_create_user(message.from_user.id)
    await message.reply(
        "ברוך הבא לבוט הלוטו החכם! 🎰\n\n"
        "כמשתמש חדש, מגיעה לך תחזית ראשונה של 10 שורות בחינם.\n"
        "לחץ על הכפתור למטה כדי להתחיל.",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('🎰 קבל 10 שורות חינם', callback_data='lotto')
        )
    )

@dp.callback_query_handler(lambda c: c.data == 'lotto')
async def process_lotto(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = get_or_create_user(user_id)
    
    # בדיקת מנוי פרימיום (תוקף)
    now = datetime.datetime.utcnow()
    is_active_premium = user.is_premium and (user.expiry_date is None or user.expiry_date > now)

    if not user.has_used_free:
        # פעם ראשונה בחינם
        results = get_lotto_predictions()
        user.has_used_free = True
        session.commit()
        await send_predictions(user_id, results, "מתנת הצטרפות: 10 שורות בחינם!")
    
    elif is_active_premium:
        # מנוי פעיל - גישה חופשית
        results = get_lotto_predictions()
        await send_predictions(user_id, results, "תחזית מנוי VIP פעילה:")
        
    else:
        # חסימה והצעה למנוי
        await bot.send_message(
            user_id,
            "🛑 **ניצלת את התחזית החינמית שלך.**\n\n"
            "כדי להמשיך לקבל תחזיות ללא הגבלה לכל ההגרלות, הצטרף למנוי ה-VIP שלנו:\n"
            "✅ רק 10 ש"ח לחודש\n"
            "✅ חידוש אוטומטי (ניתן לביטול בכל עת)\n"
            "✅ ניתוח סטטיסטי מתקדם",
            parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton('💳 הרשמה למנוי ב-PayPal', url=PAYPAL_SUB_LINK)
            )
        )

async def send_predictions(user_id, results, title):
    response_text = f"🎫 **{title}**\n\n"
    for i, row in enumerate(results, 1):
        response_text += f"{i}. {'-'.join(map(str, row[:-1]))} | חזק: {row[-1]}\n"
    await bot.send_message(user_id, response_text, parse_mode="Markdown")

# פקודת אדמין לאישור ידני או עדכון מ-Webhook
@dp.message_handler(commands=['set_premium'])
async def set_premium(message: types.Message):
    # כאן תוסיף בדיקת ADMIN_ID
    args = message.get_args().split()
    if len(args) == 2:
        target_id, days = args
        user = get_or_create_user(target_id)
        user.is_premium = True
        user.expiry_date = datetime.datetime.utcnow() + datetime.timedelta(days=int(days))
        session.commit()
        await message.reply(f"User {target_id} is now PREMIUM for {days} days.")

if __name__ == '__main__':
    from aiogram import executor
    if 'RENDER' in os.environ:
        from aiohttp import web
        server_app, port = start_server()
        loop = executor.get_event_loop()
        loop.create_task(executor.start_polling(dp, skip_updates=True))
        web.run_app(server_app, port=port)
    else:
        executor.start_polling(dp, skip_updates=True)
