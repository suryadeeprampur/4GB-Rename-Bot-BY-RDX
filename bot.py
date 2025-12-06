import os
from pyrogram import Client, idle
from plugins.cb_data import app as Client2
from config import *
import pyromod
import pyrogram.utils

# ---------------- PORT SYSTEM ------------------
PORT = int(os.environ.get("PORT", 8080))  # Default port 8080
# ------------------------------------------------

pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999

bot = Client(
    "Renamer",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
    plugins=dict(root='plugins'),
)


def run_web_server():
    """
    Simple dummy web server (needed for Koyeb/Render/Heroku)
    Bot will NOT close due to inactivity because the web server stays alive.
    """
    from flask import Flask
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Bot Running Successfully!"

    app.run(host="0.0.0.0", port=PORT)


if STRING_SESSION:
    apps = [Client2, bot]
    
    for app in apps:
        app.start()

    # Start WEB SERVER
    import threading
    threading.Thread(target=run_web_server).start()

    idle()

    for app in apps:
        app.stop()

else:
    # Start WEB SERVER
    import threading
    threading.Thread(target=run_web_server).start()

    bot.run()



# Jishu Developer 
# Don't Remove Credit 🥺
# Telegram Channel @Madflix_Bots
# Back-Up Channel @JishuBotz
# Developer @JishuDeveloper
