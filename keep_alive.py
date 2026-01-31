from aiohttp import web
import os
import json
import logging
from database_manager import set_user_premium

# הגדרת לוגים כדי שנוכל לראות את ההודעות מפייפאל ב-Render Logs
logging.basicConfig(level=logging.INFO)

async def handle_home(request):
    return web.Response(text="Bot Webhook Listener is Active!")

async def handle_paypal_webhook(request):
    """פונקציה שמקבלת את הודעת התשלום מפייפאל ומפעילה את המנוי"""
    try:
        payload = await request.json()
        event_type = payload.get('event_type')
        logging.info(f"Received PayPal Event: {event_type}")

        resource = payload.get('resource', {})
        
        # פייפאל שולח את ה-ID של המשתמש בתוך שדה שנקרא custom_id
        # אנחנו נגדיר בבוט לשלוח את ה-ID לשם
        user_id = resource.get('custom_id') or resource.get('custom')
        
        # במקרה של מנויים (Subscriptions), המזהה יכול להיות עמוק יותר
        if not user_id and 'subscriber' in resource:
            user_id = resource['subscriber'].get('custom_id')

        # אירועים שמעידים על תשלום מוצלח
        success_events = [
            'PAYMENT.SALE.COMPLETED',
            'BILLING.SUBSCRIPTION.ACTIVATED',
            'BILLING.SUBSCRIPTION.CREATED'
        ]

        if user_id and event_type in success_events:
            sub_id = resource.get('id')
            expiry = await set_user_premium(user_id, sub_id)
            logging.info(f"SUCCESS: User {user_id} upgraded to premium. Expires: {expiry}")
            
            # שליחת הודעה למשתמש בטלגרם (דרך הבוט)
            from bot import bot
            try:
                await bot.send_message(
                    user_id, 
                    "✅ <b>התשלום התקבל בהצלחה!</b>\n\n"
                    "המנוי שלך הופעל אוטומטית. מעכשיו יש לך גישה חופשית לכל התחזיות.\n"
                    f"תוקף המנוי: {expiry}\n\n"
                    "בהצלחה! 🍀",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Could not notify user {user_id}: {e}")

        return web.Response(text="OK", status=200)
    except Exception as e:
        logging.error(f"Webhook Error: {e}")
        return web.Response(text="Error", status=400)

def start_server():
    app = web.Application()
    app.router.add_get('/', handle_home)
    # הכתובת שהגדרת בפייפאל: https://lottobot-lq4u.onrender.com/webhook/paypal
    app.router.add_post('/webhook/paypal', handle_paypal_webhook)
    port = int(os.environ.get("PORT", 8080))
    return app, port
