from aiohttp import web
import os
import logging
from database_manager import set_user_premium

logging.basicConfig(level=logging.INFO)

async def handle_home(request):
    """דף בית ש-Render סורק כדי לוודא שהשרת חי"""
    return web.Response(text="LottoAI Engine is Online and Binding Successfully.")

async def handle_paypal_webhook(request):
    """קבלת הודעות תשלום מפייפאל ושדרוג המשתמש"""
    from bot import bot
    try:
        data = await request.json()
        event_type = data.get('event_type')
        resource = data.get('resource', {})
        
        user_id = resource.get('custom_id') or resource.get('custom')
        if not user_id and 'subscriber' in resource:
            user_id = resource['subscriber'].get('custom_id')

        logging.info(f"PayPal Webhook: {event_type} for User: {user_id}")

        if user_id and event_type in ['PAYMENT.SALE.COMPLETED', 'BILLING.SUBSCRIPTION.ACTIVATED']:
            expiry = await set_user_premium(user_id, resource.get('id'))
            
            msg = (
                "🎊 **התשלום אושר! המנוי שלך הופעל** 🎊\n\n"
                "הגישה לאלגוריתם נפתחה עבורך ללא הגבלה.\n"
                f"תוקף המנוי: {expiry}\n\n"
                "צא לדרך ובהצלחה בהגרלה! 🍀"
            )
            await bot.send_message(user_id, msg, parse_mode="Markdown")

        return web.Response(text="OK", status=200)
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return web.Response(text="Error", status=400)

def start_server():
    app = web.Application()
    app.router.add_get('/', handle_home)
    app.router.add_post('/webhook/paypal', handle_paypal_webhook)
    
    # Render מספק את הפורט במשתנה סביבה PORT
    port = int(os.environ.get("PORT", 8080))
    return app, port
