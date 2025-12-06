# helper/database.py
"""
MongoDB helper for RDX_RENAME_BOT
- Unlimited uploads (no uploadlimit or used_limit fields)
- Keeps original function names for compatibility
- Uses atomic increments and upserts where appropriate
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import pymongo

from helper.date import add_date
from config import DATABASE_URL, DATABASE_NAME

log = logging.getLogger(__name__)

# Ensure basic logging if not configured elsewhere
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

# Mongo setup
mongo = pymongo.MongoClient(DATABASE_URL)
db = mongo[DATABASE_NAME]
dbcol = db["user"]


# -------------------------
# Basic helpers / counters
# -------------------------

def total_user() -> int:
    """Return total number of user documents."""
    try:
        return dbcol.count_documents({})
    except Exception as e:
        log.exception("total_user error: %s", e)
        return 0


def botdata(chat_id: int) -> None:
    """
    Ensure a bot document exists (upsert).
    Keeps counters total_rename and total_size as integers.
    """
    bot_id = int(chat_id)
    try:
        dbcol.update_one(
            {"_id": bot_id},
            {"$setOnInsert": {"total_rename": 0, "total_size": 0}},
            upsert=True,
        )
    except Exception as e:
        log.exception("botdata upsert failed: %s", e)


def total_rename(chat_id: int, increment: int = 1) -> None:
    """Atomically increment total_rename by `increment` (default 1)."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$inc": {"total_rename": int(increment)}})
    except Exception as e:
        log.exception("total_rename update failed for %s: %s", chat_id, e)


def total_size(chat_id: int, file_size: int) -> None:
    """Atomically increment total_size by file_size (in bytes)."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$inc": {"total_size": int(file_size)}})
    except Exception as e:
        log.exception("total_size update failed for %s: %s", chat_id, e)


# -------------------------
# User document operations
# -------------------------

def insert(chat_id: int) -> None:
    """
    Create user document if not exists.
    No upload limit fields are created (unlimited uploads).
    """
    user_id = int(chat_id)
    user_det = {
        "_id": user_id,
        "file_id": None,
        "caption": None,
        "daily": 0,
        "date": 0,
        "usertype": "Free",
        "prexdate": None,
        "metadata": False,
        "metadata_code": "By @Madflix_Bots",
    }
    try:
        dbcol.update_one({"_id": user_id}, {"$setOnInsert": user_det}, upsert=True)
    except Exception as e:
        log.exception("insert user failed for %s: %s", user_id, e)


def addthumb(chat_id: int, file_id: str) -> None:
    """Set user's thumbnail file_id."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"file_id": file_id}})
    except Exception as e:
        log.exception("addthumb failed for %s: %s", chat_id, e)


def delthumb(chat_id: int) -> None:
    """Remove thumbnail (set file_id to None)."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"file_id": None}})
    except Exception as e:
        log.exception("delthumb failed for %s: %s", chat_id, e)


# ============= Metadata Functions ===============

def setmeta(chat_id: int, bool_meta: bool) -> None:
    """Enable/disable metadata for a user."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"metadata": bool(bool_meta)}})
    except Exception as e:
        log.exception("setmeta failed for %s: %s", chat_id, e)


def setmetacode(chat_id: int, metadata_code: str) -> None:
    """Set the metadata code (string) for a user."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"metadata_code": metadata_code}})
    except Exception as e:
        log.exception("setmetacode failed for %s: %s", chat_id, e)


# ============= Caption Functions ===============

def addcaption(chat_id: int, caption: str) -> None:
    """Add or update a user's caption."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"caption": caption}})
    except Exception as e:
        log.exception("addcaption failed for %s: %s", chat_id, e)


def delcaption(chat_id: int) -> None:
    """Remove user's caption."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"caption": None}})
    except Exception as e:
        log.exception("delcaption failed for %s: %s", chat_id, e)


# ============= Date / Premium / Daily ===============

def dateupdate(chat_id: int, date_value: Any) -> None:
    """Update the 'date' field for daily tracking."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"date": date_value}})
    except Exception as e:
        log.exception("dateupdate failed for %s: %s", chat_id, e)


def daily(chat_id: int, date_value: Any) -> None:
    """Update the 'daily' field for the user."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"daily": date_value}})
    except Exception as e:
        log.exception("daily update failed for %s: %s", chat_id, e)


def addpre(chat_id: int) -> None:
    """
    Set premium expiry date using helper.date.add_date().
    add_date() is expected to return a sequence where the first element is the date string.
    """
    try:
        date_val = add_date()
        if isinstance(date_val, (list, tuple)) and len(date_val) > 0:
            prex = date_val[0]
        else:
            prex = date_val
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"prexdate": prex}})
    except Exception as e:
        log.exception("addpre failed for %s: %s", chat_id, e)


def addpredata(chat_id: int) -> None:
    """Clear premium expiration (remove premium)."""
    try:
        dbcol.update_one({"_id": int(chat_id)}, {"$set": {"prexdate": None}})
    except Exception as e:
        log.exception("addpredata failed for %s: %s", chat_id, e)


# -------------------------
# Find / list / delete
# -------------------------

def find(chat_id: int) -> Optional[List[Any]]:
    """
    Return user info in the original list format:
    [file_id, caption, metadata, metadata_code]
    Returns None if user not found.
    """
    try:
        doc = dbcol.find_one({"_id": int(chat_id)})
        if not doc:
            return None

        file_id = doc.get("file_id")
        caption = doc.get("caption") if "caption" in doc else None
        metadata = doc.get("metadata", False)
        metadata_code = doc.get("metadata_code", None)

        return [file_id, caption, metadata, metadata_code]
    except Exception as e:
        log.exception("find failed for %s: %s", chat_id, e)
        return None


def getid() -> List[int]:
    """Return list of all user _id values as ints."""
    try:
        return [int(d["_id"]) for d in dbcol.find({}, {"_id": 1})]
    except Exception as e:
        log.exception("getid failed: %s", e)
        return []


def delete(id_value: int) -> None:
    """Delete a user document by id value."""
    try:
        dbcol.delete_one({"_id": int(id_value)})
    except Exception as e:
        log.exception("delete failed for %s: %s", id_value, e)


def find_one(id_value: int) -> Optional[Dict[str, Any]]:
    """Return the raw user document (or None)."""
    try:
        return dbcol.find_one({"_id": int(id_value)})
    except Exception as e:
        log.exception("find_one failed for %s: %s", id_value, e)
        return None


# -------------------------
# Footer credit (kept as comment)
# -------------------------
# Jishu Developer
# Don't Remove Credit 🥺
# Telegram Channel @Madflix_Bots
# Back-Up Channel @JishuBotz
# Developer @JishuDeveloper & @MadflixOfficials

    

# Jishu Developer 
# Don't Remove Credit 🥺
# Telegram Channel @Madflix_Bots
# Back-Up Channel @JishuBotz
# Developer @JishuDeveloper & @MadflixOfficials
