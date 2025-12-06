import os
import asyncio
from aiohttp import web
from pyrogram import Client, idle
from plugins.cb_data import app as Client2
from config import *
import pyrogram.utils

# Keep your existing pyrogram tweaks
pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999

# Your main bot client
bot = Client(
    "Renamer",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
    plugins=dict(root='plugins')
)

# ---------- tiny HTTP health server ----------
async def health(request):
    return web.Response(text="OK")

async def start_health_server(host="0.0.0.0", port=8080):
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/healthz", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Health server running on http://{host}:{port}/healthz")
    return runner  # return runner so we can cleanup later

# ---------- main async flow ----------
async def main():
    # Start health server first so platform health checks pass while bot boots
    runner = await start_health_server()

    # Build list of clients to start
    if STRING_SESSION:
        apps = [Client2, bot]
    else:
        apps = [bot]

    # Start each client
    for app in apps:
        print(f"Starting {getattr(app, '_session_name', repr(app))} ...")
        await app.start()
    print("All pyrogram clients started.")

    # Keep process alive until termination
    try:
        await idle()
    finally:
        print("Shutting down clients...")
        # Stop clients in reverse order just in case
        for app in reversed(apps):
            try:
                await app.stop()
            except Exception as e:
                print(f"Error stopping {app}: {e}")
        # Clean up the aiohttp runner
        try:
            await runner.cleanup()
        except Exception as e:
            print(f"Error cleaning health server: {e}")
        print("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Exited by signal")
