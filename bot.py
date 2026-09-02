Telegram-бот @Gulsumgoddnessbot
Воронка: проверка подписки → выдача PDF → follow-up
"""

import os
import logging
import sqlite3
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "flywithgulsum").lstrip("@")
GUIDE_FILE_ID = os.getenv(
    "GUIDE_FILE_ID",
    "BQACAgIAAyEGAAScYJNLAAIGtWqX52oDx-fjCeG473L63U5vhXFeAALipgACLfzASNkDq_b-JecMPQQ",
)
PDF_FILE = os.getenv("PDF_FILE", "guide.pdf")
DB_FILE = os.getenv("DB_FILE", "bot_users.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def ensure_local_pdf(app):
    if os.path.exists(PDF_FILE):
        logger.info("PDF уже есть: %s (%d байт)", PDF_FILE, os.path.getsize(PDF_FILE))
        return True
    try:
        file = await app.bot.get_file(GUIDE_FILE_ID)
        await file.download_to_drive(PDF_FILE)
        logger.info("PDF скачан в %s", PDF_FILE)
        return True
    except Exception as e:
        logger.error("Ошибка скачивания PDF: %s", e)
        return False


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id      INTEGER PRIMARY KEY,
            username     TEXT,
            first_name   TEXT,
            joined_at    TEXT,
            source       TEXT,
            guide_sent   INTEGER DEFAULT 0,
            guide_at     TEXT,
            followup_2d  INTEGER DEFAULT 0,
            followup_5d  INTEGER DEFAULT 0,
            followup_7d  INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_user(user, source="organic", guide_sent=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if guide_sent:
        c.execute(
            """
            INSERT INTO users (user_id, username, first_name, joined_at, source, guide_sent, guide_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                source=excluded.source,
                guide_sent=1,
                guide_at=excluded.guide_at
            """,
            (user.id, user.username, user.first_name, datetime.now().isoformat(), source,
             datetime.now().isoformat()),
        )
    else:
        c.execute(
            """
            INSERT INTO users (user_id, username, first_name, joined_at, source)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                source=excluded.source
            """,
            (user.id, user.username, user.first_name, datetime.now().isoformat(), source),
        )
    conn.commit()
    conn.close()
