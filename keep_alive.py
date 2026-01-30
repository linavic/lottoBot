from aiohttp import web
import os

async def handle(request):
    return web.Response(text="Bot is Alive!")

def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    port = int(os.environ.get("PORT", 8080))
    return app, port
