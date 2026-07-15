import os
import logging
import asyncio
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Your main Telegram channel
CHANNEL_USERNAME = "@avoidrep"

# Local banner file uploaded to GitHub repository
SCAMMER_BANNER = "scammer.jpg"

# Conversation states
USERNAME, DEAL_VALUE, SUMMARY, PROOF_LINK = range(4)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("avoid-reports")


# =========================================================
# RENDER HEALTH CHECK SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AVOID REPORTS BOT IS RUNNING")

    def log_message(self, format, *args):
        return


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)

    logger.info(f"Health server running on port {port}")

    server.serve_forever()


# =========================================================
# HELPERS
# =========================================================

def clean_username(value: str) -> str:
    value = value.strip()

    if value.startswith("https://t.me/"):
        value = value.replace("https://t.me/", "")

    if value.startswith("http://t.me/"):
        value = value.replace("http://t.me/", "")

    value = value.strip("/")

    if value.startswith("@"):
        value = value[1:]

    return value


def profile_url(username: str) -> str:
    username = clean_username(username)

    if username.isdigit():
        return f"tg://user?id={username}"

    return f"https://t.me/{username}"


def proof_url(link: str) -> str:
    link = link.strip()

    if link.startswith("t.me/"):
        return "https://" + link

    return link


def main_menu():
    return ReplyKeyboardMarkup(
        [["Create Report"]],
        resize_keyboard=True,
    )


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        "⚠️ *Welcome to AVOID REPORTS*\n\n"
        "Report Telegram scammers for review.\n\n"
        "All reports are reviewed before publishing.\n\n"
        f"📢 Channel: {CHANNEL_USERNAME}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Join @avoidrep ↗",
                    url="https://t.me/avoidrep"
                )
            ]
        ]
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    await update.message.reply_text(
        "Main Menu",
        reply_markup=main_menu(),
    )


# =========================================================
# CREATE REPORT
# =========================================================

async def create_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "Send scammer's Telegram @username or User ID:",
        reply_markup=ReplyKeyboardMarkup(
            [["Cancel"]],
            resize_keyboard=True,
        ),
    )

    return USERNAME


# =========================================================
# USERNAME
# =========================================================

async def get_username(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    value = update.message.text.strip()

    if value.lower() == "cancel":
        return await cancel(update, context)

    context.user_data["username"] = value

    await update.message.reply_text(
        "Enter deal value:"
    )

    return DEAL_VALUE


# =========================================================
# DEAL VALUE
# =========================================================

async def get_deal_value(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    value = update.message.text.strip()

    if value.lower() == "cancel":
        return await cancel(update, context)

    context.user_data["deal_value"] = value

    await update.message.reply_text(
        "Briefly explain the scam:"
    )

    return SUMMARY


# =========================================================
# SUMMARY
# =========================================================

async def get_summary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    value = update.message.text.strip()

    if value.lower() == "cancel":
        return await cancel(update, context)

    context.user_data["summary"] = value

    await update.message.reply_text(
        "Send proof channel link:\n"
        "Example: https://t.me/+xxxx"
    )

    return PROOF_LINK


# =========================================================
# PROOF LINK + SEND TO ADMIN
# =========================================================

async def get_proof(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    value = update.message.text.strip()

    if value.lower() == "cancel":
        return await cancel(update, context)

    if not (
        value.startswith("https://t.me/")
        or value.startswith("http://t.me/")
        or value.startswith("t.me/")
    ):
        await update.message.reply_text(
            "Please send a valid Telegram proof link."
        )
        return PROOF_LINK

    context.user_data["proof_link"] = proof_url(value)

    username = context.user_data["username"]
    deal_value = context.user_data["deal_value"]
    summary = context.user_data["summary"]
    proof = context.user_data["proof_link"]

    reporter_id = update.effective_user.id
    reporter_name = update.effective_user.full_name

    report_data = {
        "username": username,
        "deal_value": deal_value,
        "summary": summary,
        "proof": proof,
        "reporter_id": reporter_id,
        "reporter_name": reporter_name,
    }

    # Store report temporarily
    context.bot_data[f"report_{reporter_id}"] = report_data

    admin_text = (
        "🚨 *NEW REPORT*\n\n"
        f"👤 User: `{username}`\n"
        f"💰 Value: `{deal_value}`\n"
        f"📝 Summary: {summary}\n"
        f"🔗 Proof: {proof}\n\n"
        f"📨 Reporter: {reporter_name}\n"
        f"🆔 Reporter ID: `{reporter_id}`"
    )

    admin_buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Approve",
                    callback_data=f"approve:{reporter_id}"
                ),
                InlineKeyboardButton(
                    "❌ Reject",
                    callback_data=f"reject:{reporter_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "View Proofs ↗",
                    url=proof
                )
            ]
        ]
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=admin_buttons,
        )

        await update.message.reply_text(
            "✅ Report submitted for review.",
            reply_markup=main_menu(),
        )

    except Exception as e:

        logger.exception("Failed to send report to admin")

        await update.message.reply_text(
            "❌ Could not submit the report. Please try again.",
            reply_markup=main_menu(),
        )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# APPROVE REPORT
# =========================================================

async def approve_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    # Only admin can approve
    if query.from_user.id != ADMIN_CHAT_ID:

        await query.answer(
            "You are not authorized.",
            show_alert=True,
        )

        return

    reporter_id = int(
        query.data.split(":")[1]
    )

    report_key = f"report_{reporter_id}"

    report = context.bot_data.get(report_key)

    if not report:

        await query.edit_message_text(
            "⚠️ Report data expired or was already processed."
        )

        return

    username = report["username"]
    deal_value = report["deal_value"]
    summary = report["summary"]
    proof = report["proof"]

    clean_user = clean_username(username)

    # Channel post text
    channel_caption = (
        f"❌ User @{clean_user} has been marked as a scammer.\n\n"
        f"💰 Deal Value: {deal_value}\n"
        f"📝 {summary}"
    )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "View Profile ↗",
                    url=profile_url(username),
                ),
                InlineKeyboardButton(
                    "View Proofs ↗",
                    url=proof,
                ),
            ]
        ]
    )

    try:

        # Send banner + caption
        if os.path.exists(SCAMMER_BANNER):

            with open(SCAMMER_BANNER, "rb") as photo:

                sent_post = await context.bot.send_photo(
                    chat_id=CHANNEL_USERNAME,
                    photo=photo,
                    caption=channel_caption,
                    reply_markup=buttons,
                )

        else:

            # Fallback if banner missing
            sent_post = await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=channel_caption,
                reply_markup=buttons,
            )

        await query.edit_message_text(
            "✅ REPORT APPROVED\n\n"
            f"User: @{clean_user}\n"
            f"Published in {CHANNEL_USERNAME}"
        )

        # Notify reporter
        try:

            await context.bot.send_message(
                chat_id=reporter_id,
                text=(
                    "✅ Your report has been approved "
                    "and published."
                ),
                reply_markup=main_menu(),
            )

        except Exception:
            pass

        # Remove temporary data
        context.bot_data.pop(report_key, None)

    except Exception as e:

        logger.exception(
            "Failed to publish report"
        )

        await query.edit_message_text(
            "❌ Failed to publish report.\n\n"
            "Make sure the bot is an admin in @avoidrep "
            "with permission to post messages."
        )


# =========================================================
# REJECT REPORT
# =========================================================

async def reject_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_CHAT_ID:

        await query.answer(
            "You are not authorized.",
            show_alert=True,
        )

        return

    reporter_id = int(
        query.data.split(":")[1]
    )

    report_key = f"report_{reporter_id}"

    report = context.bot_data.get(report_key)

    if not report:

        await query.edit_message_text(
            "⚠️ Report already processed or expired."
        )

        return

    await query.edit_message_text(
        "❌ REPORT REJECTED"
    )

    try:

        await context.bot.send_message(
            chat_id=reporter_id,
            text="❌ Your report was not approved.",
            reply_markup=main_menu(),
        )

    except Exception:
        pass

    context.bot_data.pop(
        report_key,
        None,
    )


# =========================================================
# CANCEL
# =========================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "Report cancelled.",
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Exception while handling update:",
        exc_info=context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN environment variable is missing."
        )

    if not ADMIN_CHAT_ID:
        raise ValueError(
            "ADMIN_CHAT_ID environment variable is missing."
        )

    logger.info(
        "Starting AVOID REPORTS bot..."
    )

    # Start Render health server
    Thread(
        target=run_health_server,
        daemon=True,
    ).start()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    conversation = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"^Create Report$"
                ),
                create_report,
            ),
        ],

        states={

            USERNAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_username,
                )
            ],

            DEAL_VALUE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_deal_value,
                )
            ],

            SUMMARY: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_summary,
                )
            ],

            PROOF_LINK: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_proof,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            ),
        ],
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        conversation
    )

    application.add_handler(
        CallbackQueryHandler(
            approve_report,
            pattern=r"^approve:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            reject_report,
            pattern=r"^reject:"
        )
    )

    application.add_error_handler(
        error_handler
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
