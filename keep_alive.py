from aiohttp import web
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

# זהו קובץ שרת שמאפשר ל-Render להשאיר את הבוט דולק
# וגם מקבל הודעות תשלום מפייפאל (Webhooks)

async def handle_home(request):
    return web.Response(text="Lotto Bot is running!")

async def handle_paypal_webhook(request):
    try:
        data = await request.json()
        event_type = data.get('event_type')
        
        # התחברות למסד הנתונים לעדכון
        DATABASE_URL = os.getenv('DATABASE_URL')
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # כאן הלוגיקה לעדכון משתמש לפי אירוע פייפאל
        if event_type == 'BILLING.SUBSCRIPTION.CREATED' or event_type == 'PAYMENT.SALE.COMPLETED':
            # פייפאל שולח מזהה משתמש בתוך custom_id או בתוך ה-resource
            # תצטרך להוסיף את ה-ID של הטלגרם ב-custom_id בלינק של פייפאל
            resource = data.get('resource', {})
            custom_id = resource.get('custom_id') or resource.get('custom')
            
            if custom_id:
                from bot import User # ייבוא פנימי למניעת Circular Import
                user = db.query(User).filter_by(user_id=str(custom_id)).first()
                if user:
                    user.is_premium = True
                    user.expiry_date = datetime.datetime.now() + datetime.timedelta(days=32)
                    db.commit()
                    logging.info(f"User {custom_id} upgraded to premium via Webhook")
        
        db.close()
        return web.Response(text="Webhook received", status=200)
    except Exception as e:
        logging.error(f"Webhook Error: {e}")
        return web.Response(text="Error", status=400)

app = web.Application()
app.router.add_get('/', handle_home)
app.router.add_post('/webhook/paypal', handle_paypal_webhook)

def start_server():
    port = int(os.environ.get("PORT", 8080))
    return app, port
