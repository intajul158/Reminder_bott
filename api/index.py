import os
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from http.server import BaseHTTPRequestHandler

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("8515151596:AAHimsbY_Q6CDp7R7eoPJCQOD0Fbg3szMac")
CRON_SECRET = os.getenv("CRON_SECRET", "")

INTERVAL = 60

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# =========================================================
# STORAGE
# =========================================================
#
# IMPORTANT:
# Vercel filesystem is not permanent.
# This simple version keeps data in memory.
#
# For permanent storage, use Redis/Database later.
#

data = {
    "users": {},
    "groups": {}
}

waiting_message = set()

# =========================================================
# TELEGRAM API
# =========================================================

TELEGRAM_API = f"https://api.telegram.org/bot{8644485641:AAFJdbNKciBE3PWHIjGBplmBM1sVzeCTQg4}"


def telegram(method, payload=None):
    if payload is None:
        payload = {}

    body = json.dumps(payload).encode("utf-8")

    request = Request(
        f"{TELEGRAM_API}/{method}",
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    except HTTPError as e:
        logger.error(
            "Telegram API error: %s",
            e.read().decode("utf-8", errors="ignore")
        )
        return None

    except Exception as e:
        logger.error("Telegram request failed: %s", e)
        return None


def send_message(chat_id, text):
    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )

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


def info_command(message):
    user = message.get("from")

    if not user:
        return

    name = user.get("first_name", "")
    last_name = user.get("last_name", "")

    if last_name:
        name = f"{name} {last_name}"

    user_id = user.get("id")

    text = (
        "👤 Your Information\n\n"
        f"Name: {name}\n"
        f"Telegram User ID: {user_id}"
    )

    send_message(message["chat"]["id"], text)

# =========================================================
# /start
# =========================================================


def start_command(message):
    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_type = chat.get("type")

    if chat_type not in ["group", "supergroup"]:
        send_message(
            chat["id"],
            "ℹ️ এই কমান্ডটি Group/Supergroup-এ ব্যবহার করুন।\n\n"
            "যে কেউ এখানে /start দিয়ে reminder scheduler চালু করতে পারবে।"
        )
        return

    user_id = user.get("id")
    user_data = get_user_data(user_id)

    if not user_data.get("message", "").strip():
        send_message(
            chat["id"],
            "⚠️ আপনার কোনো reminder message সেট করা নেই।\n\n"
            "আগে Bot-এর Private Chat-এ গিয়ে:\n"
            "/setmessage\n\n"
            "দিয়ে আপনার reminder message সেট করুন।"
        )
        return

    group_id = str(chat["id"])

    data["groups"][group_id] = {
        "user_id": user_id,
        "enabled": True
    }

    name = user.get("first_name", "Unknown")

    send_message(
        chat["id"],
        "🟢 Reminder Scheduler STARTED!\n\n"
        "⏰ Interval: 1 minute\n"
        f"👤 Message owner: {name}\n\n"
        "যে কেউ /disable দিয়ে scheduler বন্ধ করতে পারবে।"
    )

# =========================================================
# /disable
# =========================================================


def disable_command(message):
    chat = message.get("chat", {})

    if chat.get("type") not in ["group", "supergroup"]:
        send_message(
            chat["id"],
            "ℹ️ এই কমান্ডটি Group/Supergroup-এ ব্যবহার করুন।"
        )
        return

    group_id = str(chat["id"])

    if group_id not in data["groups"]:
        send_message(
            chat["id"],
            "ℹ️ এই গ্রুপে scheduler চালু নেই।"
        )
        return

    data["groups"][group_id]["enabled"] = False

    send_message(
        chat["id"],
        "🔴 Reminder Scheduler STOPPED!\n\n"
        "আবার চালু করতে যেকেউ /start ব্যবহার করতে পারবে।"
    )

# =========================================================
# /status
# =========================================================


def status_command(message):
    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_type = chat.get("type")

    if chat_type in ["group", "supergroup"]:

        group_id = str(chat["id"])

        if group_id not in data["groups"]:
            send_message(
                chat["id"],
                "🔴 Scheduler Status: OFF\n\n"
                "এই গ্রুপে scheduler এখনো চালু করা হয়নি।"
            )
            return

        group_data = data["groups"][group_id]

        enabled = group_data.get("enabled", False)
        message_user_id = group_data.get("user_id")

        if enabled:
            text = (
                "🟢 Scheduler Status: ON\n\n"
                "⏰ Interval: 1 minute\n"
                f"👤 Message User ID: {message_user_id}\n\n"
                "Scheduler প্রতি ১ মিনিটে reminder পাঠাবে।"
            )
        else:
            text = (
                "🔴 Scheduler Status: OFF\n\n"
                "চালু করতে /start ব্যবহার করুন।"
            )

        send_message(chat["id"], text)
        return

    user_data = get_user_data(user["id"])
    saved_message = user_data.get("message", "")

    if saved_message.strip():

        preview = saved_message

        if len(preview) > 300:
            preview = preview[:300] + "..."

        send_message(
            chat["id"],
            "📋 Your Reminder Message\n\n"
            f"{preview}\n\n"
            "✅ Message is set."
        )

    else:
        send_message(
            chat["id"],
            "📋 Your Reminder Message\n\n"
            "❌ No message is set.\n\n"
            "Set one using /setmessage"
        )

# =========================================================
# /setmessage
# =========================================================


def setmessage_command(message):
    chat = message.get("chat", {})
    user = message.get("from", {})

    if chat.get("type") != "private":
        send_message(
            chat["id"],
            "ℹ️ Reminder message সেট করতে Bot-এর Private Chat-এ যান।\n\n"
            "তারপর /setmessage ব্যবহার করুন।"
        )
        return

    waiting_message.add(user["id"])

    send_message(
        chat["id"],
        "✏️ এখন আপনার reminder message পাঠান।\n\n"
        "আপনার পরবর্তী message-টি reminder হিসেবে save হবে।\n\n"
        "❌ Cancel করতে /cmd ব্যবহার করতে পারেন।"
    )

# =========================================================
# PRIVATE MESSAGE
# =========================================================


def private_message_handler(message):
    user = message.get("from", {})
    chat = message.get("chat", {})

    user_id = user.get("id")

    if user_id not in waiting_message:
        return

    message_text = message.get("text")

    if not message_text:
        send_message(
            chat["id"],
            "⚠️ শুধুমাত্র text message পাঠান।"
        )
        return

    user_data = get_user_data(user_id)

    user_data["message"] = message_text

    waiting_message.discard(user_id)

    send_message(
        chat["id"],
        "✅ Reminder message successfully saved!\n\n"
        f"📝 Message:\n{message_text}\n\n"
        "এখন যেকোনো group-এ গিয়ে /start দিলে "
        "scheduler চালু হবে।"
    )

# =========================================================
# /cmd
# =========================================================


def cmd_command(message):
    chat_id = message["chat"]["id"]

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

    send_message(chat_id, text)

# =========================================================
# COMMAND ROUTER
# =========================================================


def handle_update(update):
    message = update.get("message")

    if not message:
        return

    text = message.get("text", "")

    if not text:
        return

    # Commands
    if text.startswith("/info"):
        info_command(message)
        return

    if text.startswith("/start"):
        start_command(message)
        return

    if text.startswith("/disable"):
        disable_command(message)
        return

    if text.startswith("/status"):
        status_command(message)
        return

    if text.startswith("/setmessage"):
        setmessage_command(message)
        return

    if text.startswith("/cmd"):
        cmd_command(message)
        return

    # Private normal text
    if message.get("chat", {}).get("type") == "private":
        private_message_handler(message)

# =========================================================
# REMINDER SCHEDULER
# =========================================================


def send_reminders():
    logger.info("Running reminder scheduler...")

    groups = data.get("groups", {})

    for group_id, group_data in list(groups.items()):

        if not group_data.get("enabled", False):
            continue

        user_id = group_data.get("user_id")

        if not user_id:
            continue

        user_data = data["users"].get(str(user_id))

        if not user_data:
            continue

        reminder = user_data.get("message", "").strip()

        if not reminder:
            continue

        try:
            send_message(
                int(group_id),
                reminder
            )

            logger.info(
                "Reminder sent to group %s",
                group_id
            )

        except Exception as e:
            logger.error(
                "Failed to send reminder to %s: %s",
                group_id,
                e
            )

# =========================================================
# VERCEL WEBHOOK
# =========================================================


class Handler(BaseHTTPRequestHandler):

    def do_POST(self):

        content_length = int(
            self.headers.get("Content-Length", 0)
        )

        body = self.rfile.read(content_length)

        try:
            update = json.loads(
                body.decode("utf-8")
            )

            handle_update(update)

        except Exception as e:
            logger.exception(
                "Webhook error: %s",
                e
            )

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.end_headers()

        self.wfile.write(
            b'{"ok":true}'
        )

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"Reminder Bot is running!"
        )

    def log_message(self, format, *args):
        return


# Vercel Python entrypoint
handler = Handler
