import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("8644485641:AAFJdbNKciBE3PWHIjGBplmBM1sVzeCTQg4")

# Reminder interval: 60 seconds = 1 minute
INTERVAL = 60

DATA_FILE = "bot_data.json"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# TOKEN CHECK
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is missing. "
        "Please add BOT_TOKEN in Wispbyte Environment Variables."
    )


# =========================================================
# DATA
# =========================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "groups": {}
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        logger.error("Could not load data: %s", e)

        return {
            "users": {},
            "groups": {}
        }


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        logger.error("Could not save data: %s", e)


# =========================================================
# USER DATA
# =========================================================

def get_user_data(user_id):
    user_id = str(user_id)

    if user_id not in data["users"]:
        data["users"][user_id] = {
            "message": ""
        }

    return data["users"][user_id]


# =========================================================
# /info
# =========================================================

async def info_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    if not user:
        return

    name = user.full_name
    user_id = user.id

    text = (
        "👤 Your Information\n\n"
        f"Name: {name}\n"
        f"Telegram User ID: {user_id}"
    )

    await update.message.reply_text(text)


# =========================================================
# /start
# =========================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    chat = update.effective_chat
    user = update.effective_user

    # Only useful in groups
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(
            "ℹ️ এই কমান্ডটি Group/Supergroup-এ ব্যবহার করুন।\n\n"
            "যে কেউ এখানে /start দিয়ে reminder scheduler চালু করতে পারবে।"
        )
        return

    user_data = get_user_data(user.id)

    # Check if message exists
    if not user_data.get("message", "").strip():
        await update.message.reply_text(
            "⚠️ আপনার কোনো reminder message সেট করা নেই।\n\n"
            "আগে Bot-এর Private Chat-এ গিয়ে:\n"
            "/setmessage\n\n"
            "দিয়ে আপনার reminder message সেট করুন।"
        )
        return

    group_id = str(chat.id)

    # Save group settings
    data["groups"][group_id] = {
        "user_id": user.id,
        "enabled": True
    }

    save_data()

    await update.message.reply_text(
        "🟢 Reminder Scheduler STARTED!\n\n"
        "⏰ Interval: 1 minute\n"
        "👤 Message owner: "
        f"{user.full_name}\n\n"
        "যে কেউ /disable দিয়ে scheduler বন্ধ করতে পারবে।"
    )


# =========================================================
# /disable
# =========================================================

async def disable_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    chat = update.effective_chat

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(
            "ℹ️ এই কমান্ডটি Group/Supergroup-এ ব্যবহার করুন।"
        )
        return

    group_id = str(chat.id)

    if group_id not in data["groups"]:
        await update.message.reply_text(
            "ℹ️ এই গ্রুপে scheduler চালু নেই।"
        )
        return

    data["groups"][group_id]["enabled"] = False

    save_data()

    await update.message.reply_text(
        "🔴 Reminder Scheduler STOPPED!\n\n"
        "আবার চালু করতে যেকেউ /start ব্যবহার করতে পারবে।"
    )


# =========================================================
# /status
# =========================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    chat = update.effective_chat
    user = update.effective_user

    # Group status
    if chat.type in ["group", "supergroup"]:

        group_id = str(chat.id)

        if group_id not in data["groups"]:
            await update.message.reply_text(
                "🔴 Scheduler Status: OFF\n\n"
                "এই গ্রুপে scheduler এখনো চালু করা হয়নি।"
            )
            return

        group_data = data["groups"][group_id]

        enabled = group_data.get("enabled", False)
        message_user_id = group_data.get("user_id")

        if enabled:
            message = (
                "🟢 Scheduler Status: ON\n\n"
                "⏰ Interval: 1 minute\n"
                f"👤 Message User ID: {message_user_id}\n\n"
                "Scheduler প্রতি ১ মিনিটে reminder পাঠাবে।"
            )
        else:
            message = (
                "🔴 Scheduler Status: OFF\n\n"
                "চালু করতে /start ব্যবহার করুন।"
            )

        await update.message.reply_text(message)
        return

    # Private status
    user_data = get_user_data(user.id)

    saved_message = user_data.get("message", "")

    if saved_message.strip():
        preview = saved_message

        if len(preview) > 300:
            preview = preview[:300] + "..."

        await update.message.reply_text(
            "📋 Your Reminder Message\n\n"
            f"{preview}\n\n"
            "✅ Message is set."
        )

    else:
        await update.message.reply_text(
            "📋 Your Reminder Message\n\n"
            "❌ No message is set.\n\n"
            "Set one using /setmessage"
        )


# =========================================================
# /setmessage
# =========================================================

async def setmessage_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    chat = update.effective_chat

    # Only allow message setup in private chat
    if chat.type != "private":
        await update.message.reply_text(
            "ℹ️ Reminder message সেট করতে Bot-এর Private Chat-এ যান।\n\n"
            "তারপর /setmessage ব্যবহার করুন।"
        )
        return

    context.user_data["waiting_message"] = True

    await update.message.reply_text(
        "✏️ এখন আপনার reminder message পাঠান।\n\n"
        "আপনার পরবর্তী message-টি reminder হিসেবে save হবে।\n\n"
        "❌ Cancel করতে /cmd ব্যবহার করতে পারেন।"
    )


# =========================================================
# PRIVATE TEXT MESSAGE
# =========================================================

async def private_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    if not update.effective_user:
        return

    # Only process if user is waiting to set a message
    if not context.user_data.get("waiting_message", False):
        return

    user_id = update.effective_user.id
    message_text = update.message.text

    if not message_text:
        await update.message.reply_text(
            "⚠️ শুধুমাত্র text message পাঠান।"
        )
        return

    # Save message
    user_data = get_user_data(user_id)
    user_data["message"] = message_text

    # Stop waiting
    context.user_data["waiting_message"] = False

    save_data()

    await update.message.reply_text(
        "✅ Reminder message successfully saved!\n\n"
        f"📝 Message:\n{message_text}\n\n"
        "এখন যেকোনো group-এ গিয়ে /start দিলে "
        "scheduler চালু হবে।"
    )


# =========================================================
# /cmd
# =========================================================

async def cmd_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    text = (
        "🤖 Available Commands\n\n"

        "/info\n"
        "• আপনার Telegram User ID দেখাবে\n\n"

        "/setmessage\n"
        "• Reminder message সেট করুন\n\n"

        "/start\n"
        "• Reminder scheduler চালু করুন\n"
        "• যে কেউ ব্যবহার করতে পারবে\n\n"

        "/disable\n"
        "• Reminder scheduler বন্ধ করুন\n"
        "• যে কেউ ব্যবহার করতে পারবে\n\n"

        "/status\n"
        "• Scheduler-এর বর্তমান status দেখুন\n\n"

        "/cmd\n"
        "• এই command list দেখুন\n\n"

        "⏰ Reminder Interval: 1 minute\n\n"

        "ℹ️ কোনো Admin/Owner permission নেই।\n"
        "Group-এর যেকোনো member scheduler Start/Stop করতে পারবে।"
    )

    await update.message.reply_text(text)


# =========================================================
# REMINDER SCHEDULER
# =========================================================

async def send_reminders(
    context: ContextTypes.DEFAULT_TYPE
):
    logger.info("Running reminder scheduler...")

    groups = data.get("groups", {})

    for group_id, group_data in list(groups.items()):

        # Scheduler disabled
        if not group_data.get("enabled", False):
            continue

        user_id = group_data.get("user_id")

        if not user_id:
            continue

        user_data = data["users"].get(str(user_id))

        if not user_data:
            logger.warning(
                "User data not found for user_id=%s",
                user_id
            )
            continue

        message = user_data.get("message", "").strip()

        if not message:
            logger.warning(
                "No reminder message for user_id=%s",
                user_id
            )
            continue

        try:
            await context.bot.send_message(
                chat_id=int(group_id),
                text=message
            )

            logger.info(
                "Reminder sent to group %s",
                group_id
            )

        except Exception as e:
            logger.error(
                "Failed to send reminder to group %s: %s",
                group_id,
                e
            )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.error(
        "Exception while handling update:",
        exc_info=context.error
    )


# =========================================================
# WISPBYTE HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()
        self.wfile.write(
            b"Bot is running!"
        )

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.getenv("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    logger.info(
        "Health server running on port %s",
        port
    )

    server.serve_forever()


# =========================================================
# MAIN
# =========================================================

def main():

    # Start health server
    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    # Create Telegram application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("info", info_command)
    )

    application.add_handler(
        CommandHandler("start", start_command)
    )

    application.add_handler(
        CommandHandler("disable", disable_command)
    )

    application.add_handler(
        CommandHandler("status", status_command)
    )

    application.add_handler(
        CommandHandler("setmessage", setmessage_command)
    )

    application.add_handler(
        CommandHandler("cmd", cmd_command)
    )

    # Private message handler
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            private_message_handler
        )
    )

    # Error handler
    application.add_error_handler(error_handler)

    # Scheduler
    application.job_queue.run_repeating(
        send_reminders,
        interval=INTERVAL,
        first=INTERVAL,
        name="reminder_scheduler"
    )

    logger.info("Bot starting...")
    logger.info("Reminder interval: %s seconds", INTERVAL)

    # Start bot
    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()