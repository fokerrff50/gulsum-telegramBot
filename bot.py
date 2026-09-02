""" Telegram-бот @Gulsumgoddnessbot Воронка: проверка подписки → выдача PDF → follow-up Поддержка deep-link приветствия для тех, кто пришёл из канала """

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
        """ CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT, source TEXT, guide_sent INTEGER DEFAULT 0, guide_at TEXT, followup_2d INTEGER DEFAULT 0, followup_5d INTEGER DEFAULT 0, followup_7d INTEGER DEFAULT 0 ) """
    )
    conn.commit()
    conn.close()


def upsert_user(user, source="organic", guide_sent=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if guide_sent:
        c.execute(
            """ INSERT INTO users (user_id, username, first_name, joined_at, source, guide_sent, guide_at) VALUES (?, ?, ?, ?, ?, 1, ?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, source=excluded.source, guide_sent=1, guide_at=excluded.guide_at """,
            (user.id, user.username, user.first_name, datetime.now().isoformat(), source,
             datetime.now().isoformat()),
        )
    else:
        c.execute(
            """ INSERT INTO users (user_id, username, first_name, joined_at, source) VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, source=excluded.source """,
            (user.id, user.username, user.first_name, datetime.now().isoformat(), source),
        )
    conn.commit()
    conn.close()


def mark_followup(user_id, which):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"UPDATE users SET followup_{which}=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error("Ошибка проверки подписки: %s", e)
        return False


async def send_guide(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user):
    if not os.path.exists(PDF_FILE):
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ой, что-то пошло не так с гайдом 😢 Попробуй ещё раз через минуту — напиши TRAVEL.",
        )
        return
    try:
        with open(PDF_FILE, "rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename="gulsum_travel_guide.pdf",
                caption=(
                    "Готово! 🤍\n\n"
                    "Вот твой гайд — 17 страниц лайфхаков, мои кейсы, мои ошибки.\n\n"
                    "📌 Сохрани файл и перешли подруге, которая мечтает о путешествиях.\n"
                    "Хорошего дня! 🌸\n\n"
                    "Гульсум · @gulsumgoddness"
                ),
            )
        upsert_user(user, guide_sent=True)
        asyncio.create_task(schedule_followup(chat_id, context))
    except Exception as e:
        logger.error("Ошибка отправки гайда: %s", e)
        await context.bot.send_message(chat_id=chat_id, text="Ой, ошибка 😢 Попробуй ещё раз позже.")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args  # то, что после /start, например "channel" из ссылки t.me/bot?start=channel

    source = "organic"
    if args and len(args) > 0:
        source = args[0]
        logger.info("Пользователь %s пришёл из источника: %s", user.id, source)

    upsert_user(user, source=source)

    # Разные приветствия в зависимости от источника
    if source == "channel":
        text = (
            "Привет! 🤍 Вижу, что ты подписан(а) на @flywithgulsum — отлично!\n\n"
            "Я — Гульсум, помогаю путешествовать выгоднее.\n\n"
            "У меня есть гайд на 17 страниц:\n"
            "✓ Как находить билеты в 2–3 раза дешевле\n"
            "✓ Как получить €250–€600 за отмену рейса\n"
            "✓ Что делать при потере багажа\n"
            "✓ Как я путешествую через Travel Advantage\n\n"
            "Нажми кнопку — пришлю PDF 👇"
        )
    else:
        text = (
            "Привет! 🤍\n\n"
            "Я — Гульсум, помогаю путешествовать выгоднее.\n\n"
            "У меня есть гайд на 17 страниц:\n"
            "✓ Как находить билеты в 2–3 раза дешевле\n"
            "✓ Как получить €250–€600 за отмену рейса\n"
            "✓ Что делать при потере багажа\n"
            "✓ Как я путешествую через Travel Advantage\n\n"
            "Нажми кнопку ниже — пришлю PDF 👇"
        )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎁 Получить гайд", callback_data="get_guide")]]
    )
    await update.message.reply_text(text, reply_markup=keyboard)


async def on_get_guide_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    user = query.from_user
    upsert_user(user)
    chat_id = query.message.chat_id

    if await is_subscribed(user.id, context):
        try:
            await query.edit_message_text("Отлично, ты с нами! Отправляю гайд…")
        except Exception:
            pass
        await send_guide(chat_id, context, user)
    else:
        await ask_subscribe(chat_id, context, query=query)


async def ask_subscribe(chat_id, context, query=None):
    text = (
        f"Чтобы получить гайд, подпишись на канал @{CHANNEL_USERNAME} "
        "и нажми «Проверить» 👇"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"📢 Подписаться на @{CHANNEL_USERNAME}",
                    url=f"https://t.me/{CHANNEL_USERNAME}",
                ),
                InlineKeyboardButton("✅ Проверить", callback_data="check_sub"),
            ]
        ]
    )
    if query:
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.warning("edit_message_text: %s", e)
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)


async def on_check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer("Проверяю…")
    except Exception:
        pass
    user = query.from_user
    chat_id = query.message.chat_id

    if await is_subscribed(user.id, context):
        try:
            await query.edit_message_text("Отлично, ты с нами! Отправляю гайд…")
        except Exception:
            pass
        await send_guide(chat_id, context, user)
    else:
        await ask_subscribe(chat_id, context, query=query)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().upper()
    if text == "TRAVEL":
        await request_guide_from_message(update, context)
    elif text == "ПАРТНЁР":
        await partner_message(update)
    elif text == "РАЗБОР":
        await razbor_message(update)
    else:
        await update.message.reply_text(
            "Я понимаю слова-ключи:\n\n"
            "• TRAVEL — получить гайд\n"
            "• ПАРТНЁР — узнать о модели\n"
            "• РАЗБОР — консультация\n\n"
            "Напиши одно из них 👆"
        )


async def request_guide_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user)
    if await is_subscribed(user.id, context):
        await update.message.reply_text("Отлично, ты с нами! Отправляю гайд…")
        await send_guide(update.effective_chat.id, context, user)
    else:
        await ask_subscribe(update.effective_chat.id, context)


async def partner_message(update: Update):
    await update.message.reply_text(
        "Привет! 🤍\n\n"
        "Рада, что тебе интересно. Я развиваю партнёрство в Travel Advantage "
        "и беру в команду людей, которые любят путешествовать так же, как я.\n\n"
        "Что важно понимать заранее:\n"
        "— Размер вознаграждения зависит от твоей активности\n"
        "— Никто не может гарантировать конкретный доход\n"
        "— Я не обещаю лёгких денег\n\n"
        "Если хочешь узнать, как устроена модель — напиши «РАЗБОР».\n\n"
        "Гульсум · @gulsumgoddness"
    )


async def razbor_message(update: Update):
    await update.message.reply_text(
        "Отлично! 🤍\n\n"
        "Напиши, пожалуйста:\n\n"
        "1. Какое направление интересно (или открытые варианты)?\n"
        "2. Когда планируешь поездку?\n"
        "3. Что важнее — экономия или новый опыт?\n\n"
        "Отвечу в течение 24 часов.\n\n"
        "Гульсум · @gulsumgoddness"
    )


async def schedule_followup(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(2 * 24 * 60 * 60)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Привет! Как гайд — удалось что-то применить? 😊\n\n"
                "Если уже выбрала направление или есть вопросы — расскажи, "
                "могу помочь разобрать под твои даты и бюджет.\n\n"
                "Если что-то непонятно — тоже спрашивай 🤍"
            ),
        )
        mark_followup(chat_id, "2d")
    except Exception as e:
        logger.error("Followup 2d failed: %s", e)

    await asyncio.sleep(3 * 24 * 60 * 60)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Привет! 🤍\n\n"
                "Подумала — может, тебе полезно не только прочитать гайд, "
                "а разобрать твою конкретную ситуацию?\n\n"
                "Могу за 15 минут:\n"
                "— показать направления, актуальные сейчас\n"
                "— подсказать, как зайти в Travel Advantage\n"
                "— ответить на любые вопросы по лайфхакам\n\n"
                "Напиши «РАЗБОР» — назначим время."
            ),
        )
        mark_followup(chat_id, "5d")
    except Exception as e:
        logger.error("Followup 5d failed: %s", e)

    await asyncio.sleep(2 * 24 * 60 * 60)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Привет! 🤍\n\n"
                "Знаю, что не всем интересна эта тема, и это нормально.\n\n"
                "Но на всякий случай: я развиваю партнёрство в Travel Advantage "
                "и иногда беру в команду людей, которые любят путешествовать.\n\n"
                "Если когда-нибудь захочешь узнать, как это устроено — "
                "просто напиши «ПАРТНЁР».\n\n"
                "Без давления и обещаний лёгких денег.\n"
                "Хорошего дня! 🌸"
            ),
        )
        mark_followup(chat_id, "7d")
    except Exception as e:
        logger.error("Followup 7d failed: %s", e)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан.")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    async def post_init(application):
        await ensure_local_pdf(application)

    app.post_init = post_init

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_get_guide_click, pattern="get_guide"))
    app.add_handler(CallbackQueryHandler(on_check_sub, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    logger.info("Бот запущен. Канал: @%s", CHANNEL_USERNAME)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
