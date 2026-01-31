from aiohttp import web
import os
import logging

logging.basicConfig(level=logging.INFO)

async def handle_home(request):
    return web.Response(text="LottoAI Engine is Running and Binding Successfully.")

async def handle_paypal_webhook(request):
    from database_manager import set_user_premium
    from bot import bot
    try:
        data = await request.json()
        event_type = data.get('event_type')
        resource = data.get('resource', {})
        user_id = resource.get('custom_id') or resource.get('custom')
        if not user_id and 'subscriber' in resource:
            user_id = resource['subscriber'].get('custom_id')

        if user_id and event_type in ['PAYMENT.SALE.COMPLETED', 'BILLING.SUBSCRIPTION.ACTIVATED']:
            expiry = await set_user_premium(user_id, resource.get('id'))
            await bot.send_message(user_id, f"🎊 **המנוי הופעל!** 🎊\n\nתוקף: {expiry}\nבהצלחה! 🍀", parse_mode="Markdown")
        return web.Response(text="OK", status=200)
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return web.Response(text="Error", status=400)

def start_server():
    app = web.Application()
    app.router.add_get('/', handle_home)
    app.router.add_post('/webhook/paypal', handle_paypal_webhook)
    port = int(os.environ.get("PORT", 8080))
    return app, port
