from datetime import date as date_
import datetime
import os
import re
import random
import asyncio
import time
import humanize
import logging

from script import *
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.file_id import FileId

# helper modules - adjust these imports if your helpers differ
from helper.progress import humanbytes
from helper.database import (
    botdata,
    find_one,
    total_user,
    insert,
    used_limit,
    usertype,
    uploadlimit,
    addpredata,
    total_rename,
    total_size,
    daily as daily_,
)
from helper.date import check_expi
from config import *

logger = logging.getLogger(__name__)


@Client.on_message(filters.private & filters.command(["start"]))
async def start(client, message):
    user_id = message.chat.id
    try:
        old = insert(int(user_id))
    except Exception as e:
        logger.exception("insert() failed for user %s: %s", user_id, e)

    try:
        _id = message.text.split(' ')[1]
    except Exception:
        _id = None

    try:
        loading_sticker_message = await message.reply_sticker(
            "CAACAgIAAxkBAALmzGXSSt3ppnOsSl_spnAP8wHC26jpAAJEGQACCOHZSVKp6_XqghKoHgQ"
        )
        await asyncio.sleep(2)
        await loading_sticker_message.delete()
    except Exception:
        # sticker may fail in channels or for some clients — ignore
        pass

    text = (
        f"Hello {message.from_user.mention} \n\n"
        "➻ This Is An Advanced And Yet Powerful Rename Bot.\n\n"
        "➻ Using This Bot You Can Rename And Change Thumbnail Of Your Files.\n\n"
        "➻ You Can Also Convert Video To File Aɴᴅ File To Video.\n\n"
        "➻ This Bot Also Supports Custom Thumbnail And Custom Caption.\n\n"
        "<b>Bot Is Made By @Madflix_Bots</b>"
    )

    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates", url="https://t.me/Madflix_Bots"),
         InlineKeyboardButton("💬 Support", url="https://t.me/MadflixBots_Support")],
        [InlineKeyboardButton("🛠️ Help", callback_data='help'),
         InlineKeyboardButton("❤️‍🩹 About", callback_data='about')],
        [InlineKeyboardButton("🧑‍💻 Developer 🧑‍💻", url="https://t.me/MadflixOfficials")]
    ])

    try:
        await message.reply_photo(
            photo=START_PIC,
            caption=text,
            reply_markup=button,
            quote=True
        )
    except Exception as e:
        # fallback: text message if photo fails
        logger.warning("reply_photo failed: %s", e)
        await message.reply_text(text, reply_markup=button)


@Client.on_message(
    (filters.private & (filters.document | filters.audio | filters.video)) |
    (filters.channel & (filters.document | filters.audio | filters.video))
)
async def send_doc(client, message):
    """
    Robust file handler for rename bot.
    Uses safe .get() for DB fields and defensive checks to avoid KeyError.
    """
    # ensure user exists in DB
    try:
        _ = insert(int(message.chat.id))
    except Exception:
        # ignore insertion error; find_one below handles None
        pass

    # canonical user id (for private chats)
    user_id = message.from_user.id if message.from_user else message.chat.id

    # FORCE_SUBS check
    if FORCE_SUBS:
        try:
            await client.get_chat_member(FORCE_SUBS, user_id)
        except UserNotParticipant:
            _newus = find_one(user_id) or {}
            user_plan = _newus.get("usertype", "Free")
            await message.reply_text(
                "<b>Hello Dear \n\nYou Need To Join In My Channel To Use Me\n\nKindly Please Join Channel</b>",
                reply_to_message_id=message.id,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔺 Update Channel 🔺",
                                                                          url=f"https://t.me/{FORCE_SUBS}")]])
            )
            # log to LOG_CHANNEL if available
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"<b><u>New User Started The Bot</u></b> \n\n"
                    f"<b>User ID :</b> <code>{user_id}</code> \n"
                    f"<b>First Name :</b> {getattr(message.from_user, 'first_name', '')} \n"
                    f"<b>Last Name :</b> {getattr(message.from_user, 'last_name', '')} \n"
                    f"<b>User Name :</b> @{getattr(message.from_user, 'username', '')} \n"
                    f"<b>User Mention :</b> {getattr(message.from_user, 'mention', '')} \n"
                    f"<b>User Link :</b> <a href='tg://openmessage?user_id={user_id}'>Click Here</a> \n"
                    f"<b>User Plan :</b> {user_plan}"
                )
            except Exception:
                logger.exception("Failed to send log message for new user %s", user_id)
            return

    # Resolve botid safely (fix for NameError)
    try:
        botid = None
        # attempt: check for bot id passed in message.text or caption (deep-link args)
        arg_src = (getattr(message, 'text', None) or getattr(message, 'caption', None) or '').strip()
        parts = arg_src.split()
        if len(parts) > 1 and parts[1].isdigit():
            botid = int(parts[1])
        else:
            env_botid = os.getenv('BOT_ID') or os.getenv('BOTID')
            if env_botid and env_botid.isdigit():
                botid = int(env_botid)
            else:
                # fallback to bot's own id
                me = await client.get_me()
                botid = int(getattr(me, 'id', message.chat.id))
    except Exception:
        logger.exception('Failed to resolve botid, defaulting to chat id')
        botid = message.chat.id

    # update or fetch bot stats
    try:
        botdata(int(botid))
    except Exception:
        logger.exception("botdata() call failed for botid %s", botid)

    bot_data = find_one(int(botid)) or {}
    prrename = bot_data.get('total_rename', 0)
    prsize = bot_data.get('total_size', 0)

    # user details - safe gets
    user_deta = find_one(user_id) or {}
    used_date = user_deta.get("date", 0)
    buy_date = user_deta.get("prexdate")      # may be None
    daily = user_deta.get("daily", 0)
    user_type = user_deta.get("usertype", "Free")

    c_time = time.time()

    # choose LIMIT by plan (you previously had Free=120, else=10)
    LIMIT = 120 if user_type == "Free" else 10

    then = used_date + LIMIT
    left = round(then - c_time)
    conversion = datetime.timedelta(seconds=left)
    ltime = str(conversion)

    if left > 0:
        await message.reply_text(
            f"<b>Sorry Dude I Am Not Only For You \n\nFlood Control Is Active So Please Wait For {ltime} </b>",
            reply_to_message_id=message.id
        )
        return

    # retrieve file object
    media = await client.get_messages(message.chat.id, message.id)
    file = media.document or media.video or media.audio
    if not file:
        await message.reply_text("Couldn't find a file in the message.", quote=True)
        return

    # decode DC id, safe filename access
    try:
        dcid = FileId.decode(file.file_id).dc_id
    except Exception:
        dcid = "Unknown"
    filename = getattr(file, "file_name", "Unknown")
    file_id = file.file_id
    value = 2147483648  # 2GB

    # user's usage info
    used_ = find_one(user_id) or {}
    used = used_.get("used_limit", 0)
    limit = used_.get("uploadlimit", 0)

    # daily reset logic - safe
    try:
        today_str = str(date_.today())
        expi = daily - int(time.mktime(time.strptime(today_str, '%Y-%m-%d')))
    except Exception:
        expi = None

    if expi != 0:
        # reset daily and used counters
        try:
            today = date_.today()
            pattern = '%Y-%m-%d'
            epcho = int(time.mktime(time.strptime(str(today), pattern)))
            daily_(user_id, epcho)
            used_limit(user_id, 0)
        except Exception:
            logger.exception("Failed to reset daily/used for user %s", user_id)

    # check remaining quota
    remain = limit - used
    if remain < int(file.file_size):
        await message.reply_text(
            f"100% Of Daily {humanbytes(limit)} Data Quota Exhausted.\n\n"
            f"<b>File Size Detected :</b> {humanbytes(file.file_size)}\n"
            f"<b>Used Daily Limit :</b> {humanbytes(used)}\n\n"
            f"You Have Only <b>{humanbytes(remain)}</b> Left On Your Account.\n\n"
            f"If U Want To Rename Large File Upgrade Your Plan",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Upgrade", callback_data="upgrade")]])
        )
        return

    # if file is greater than 2GB
    if value < file.file_size:
        # if bot supports session-based premium checks
        if STRING_SESSION:
            # if user has no buy_date treat as no premium
            if not buy_date:
                await message.reply_text(
                    "You Can't Upload More Than 2GB File.\n\nYour Plan Doesn't Allow To Upload Files That Are Larger Than 2GB.\n\nUpgrade Your Plan To Rename Files Larger Than 2GB.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Upgrade", callback_data="upgrade")]])
                )
                return

            # check expiry
            try:
                pre_check = check_expi(buy_date)
            except Exception:
                pre_check = False

            if pre_check:
                # premium active -> allow rename prompt
                await message.reply_text(
                    f"__What Do You Want Me To Do With This File ?__\n\n"
                    f"**File Name :** `{filename}`\n"
                    f"**File Size :** {humanize.naturalsize(file.file_size)}\n"
                    f"**DC ID :** {dcid}",
                    reply_to_message_id=message.id,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 Rename", callback_data="rename"),
                                                       InlineKeyboardButton("✖️ Cancel", callback_data="cancel")]])
                )
                try:
                    total_rename(int(botid), prrename)
                    total_size(int(botid), prsize, file.file_size)
                except Exception:
                    logger.exception("Failed to update totals for bot %s", botid)
            else:
                # expired: downgrade
                try:
                    uploadlimit(user_id, 2147483648)
                    usertype(user_id, "Free")
                except Exception:
                    logger.exception("Failed to downgrade expired user %s", user_id)
                expired_str = str(buy_date) if buy_date else "Unknown"
                await message.reply_text(f'Your Plan Expired On {expired_str}', quote=True)
                return
        else:
            # no session support -> cannot handle >2GB
            await message.reply_text(
                "You Can't Upload More Than 2GB File.\n\nYour Plan Doesn't Allow To Upload Files That Are Larger Than 2GB.\n\nUpgrade Your Plan To Rename Files Larger Than 2GB.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Upgrade", callback_data="upgrade")]])
            )
            return
    else:
        # file <= 2GB path
        if buy_date:
            try:
                pre_check = check_expi(buy_date)
            except Exception:
                pre_check = False

            if pre_check is False:
                try:
                    uploadlimit(user_id, 2147483648)
                    usertype(user_id, "Free")
                except Exception:
                    logger.exception("Failed to downgrade user after expiry %s", user_id)

        filesize = humanize.naturalsize(file.file_size)
        fileid = file.file_id
        try:
            total_rename(int(botid), prrename)
            total_size(int(botid), prsize, file.file_size)
        except Exception:
            logger.exception("Failed to update total_rename/total_size for bot %s", botid)

        await message.reply_text(
            f"__What Do You Want Me To Do With This File ?__\n\n"
            f"**File Name :** `{filename}`\n"
            f"**File Size :** {filesize}\n"
            f"**DC ID :** {dcid}",
            reply_to_message_id=message.id,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 Rename", callback_data="rename"),
                                               InlineKeyboardButton("✖️ Cancel", callback_data="cancel")]])
        )


# Optional migration helper (run once if you want to ensure all user docs have 'prexdate')
# Uncomment and run separately (not as part of bot startup) if you use motor or similar async client.
"""
# Example migration using motor (async) - adapt MONGO_URI, db and collection names to your setup.
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "your_db_name"
USERS_COLLECTION = "users"

async def add_prexdate_default():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users = db[USERS_COLLECTION]
    result = await users.update_many({"prexdate": {"$exists": False}}, {"$set": {"prexdate": None}})
    print("matched:", result.matched_count, "modified:", result.modified_count)
    await client.close()

# asyncio.run(add_prexdate_default())
"""

# End of start.py
