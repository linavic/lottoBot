from aiohttp import web
import os

async def handle(request):
    return web.Response(text="Bot is Alive and Running!")

def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    # Render מספק את הפורט במשתנה סביבה בשם PORT
    port = int(os.environ.get("PORT", 8080))
    return app, port
