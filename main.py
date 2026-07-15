import os
import re
import logging
from html import escape
from urllib.parse import urlparse

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
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
# CONFIGURATION
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Where pending reports are sent for admin review.
# Example:
# -1001234567890
# OR
# 123456789
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()

# Your public channel username
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@avoidrep").strip()

# Banner URL used when an approved scam report is published.
# Example:
# https://example.com/your-banner.jpg
SCAM_BANNER_URL = os.getenv("SCAM_BANNER_URL", "").strip()


if not CHANNEL_USERNAME.startswith("@"):
    CHANNEL_USERNAME = "@" + CHANNEL_USERNAME


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("avoid-reports")


# =========================================================
# CONVERSATION STATES
# =========================================================

USERNAME, AMOUNT, SUMMARY, PROOF_LINK = range(4)


# =========================================================
# MEMORY STORAGE
# =========================================================
# This stores pending reports while the bot is running.
# For permanent storage later, a database can be added.

pending_reports = {}

report_counter = 0


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_admin_chat_id():
    """
    Converts ADMIN_CHAT_ID from environment variable
    into int where possible.
    """
    if not ADMIN_CHAT_ID_RAW:
        return None

    try:
        return int(ADMIN_CHAT_ID_RAW)
    except ValueError:
        return ADMIN_CHAT_ID_RAW


def channel_url():
    """
    Converts @avoidrep into:
    https://t.me/avoidrep
    """
    return f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"


def main_menu_keyboard():
    """
    Main menu keyboard.
    """
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Create Report")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Choose an option",
    )


def normalize_telegram_target(value: str):
    """
    Accepts:
    @username
    username
    t.me/username
    https://t.me/username
    numeric Telegram user ID

    Returns:
    {
        "type": "username",
        "value": "@username",
        "username": "username"
    }

    OR

    {
        "type": "id",
        "value": "123456789",
        "username": None
    }

    Returns None if invalid.
    """

    if not value:
        return None

    value = value.strip()

    # -----------------------------------------
    # Numeric Telegram ID
    # -----------------------------------------

    if re.fullmatch(r"-?\d{5,20}", value):
        return {
            "type": "id",
            "value": value,
            "username": None,
        }

    # -----------------------------------------
    # Telegram link
    # -----------------------------------------

    lower_value = value.lower()

    if lower_value.startswith(
        (
            "https://t.me/",
            "http://t.me/",
            "t.me/",
            "https://telegram.me/",
            "http://telegram.me/",
            "telegram.me/",
        )
    ):

        if not lower_value.startswith(("http://", "https://")):
            value = "https://" + value

        try:
            parsed = urlparse(value)

            path = parsed.path.strip("/")

            if not path:
                return None

            username = path.split("/")[0]

        except Exception:
            return None

        # Reject private invite links
        if username.startswith("+"):
            return None

        if username.lower() == "joinchat":
            return None

        value = username

    # -----------------------------------------
    # Remove @
    # -----------------------------------------

    value = value.lstrip("@").strip()

    # -----------------------------------------
    # Telegram username validation
    #
    # 5 to 32 characters
    # letters
    # numbers
    # underscores
    # -----------------------------------------

    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", value):
        return None

    return {
        "type": "username",
        "value": f"@{value}",
        "username": value,
    }


def normalize_proof_link(value: str):
    """
    Accepts private Telegram channel invite links.

    Examples:
    https://t.me/+ABC123
    t.me/+ABC123
    https://t.me/joinchat/ABC123
    """

    if not value:
        return None

    value = value.strip()

    if value.startswith("t.me/"):
        value = "https://" + value

    if value.startswith("telegram.me/"):
        value = "https://" + value

    valid_patterns = [
        r"^https://t\.me/\+[A-Za-z0-9_-]+$",
        r"^https://t\.me/joinchat/[A-Za-z0-9_-]+$",
        r"^https://telegram\.me/\+[A-Za-z0-9_-]+$",
        r"^https://telegram\.me/joinchat/[A-Za-z0-9_-]+$",
    ]

    for pattern in valid_patterns:
        if re.fullmatch(pattern, value):
            return value

    return None


def build_profile_url(report):
    """
    Creates profile URL when username is available.
    """

    username = report.get("target_username")

    if username:
        return f"https://t.me/{username}"

    return None


def clean_amount(value: str):
    """
    Keeps amount short and clean.
    """

    value = value.strip()

    if len(value) > 30:
        return None

    return value


def clean_summary(value: str):
    """
    Short summary only.
    """

    value = " ".join(value.split())

    if len(value) < 2:
        return None

    if len(value) > 250:
        return None

    return value


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Shows welcome message and main menu.
    """

    context.user_data.clear()

    text = (
        "⚠️ <b>Welcome to AVOID REPORTS</b>\n\n"
        "Report Telegram scammers for review.\n"
        "All reports are reviewed before publishing.\n\n"
        f"📢 Channel: {escape(CHANNEL_USERNAME)}"
    )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"Join {CHANNEL_USERNAME}",
                    url=channel_url(),
                )
            ]
        ]
    )

    await update.message.reply_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=buttons,
        disable_web_page_preview=True,
    )

    await update.message.reply_text(
        "Main Menu",
        reply_markup=main_menu_keyboard(),
    )


# =========================================================
# CREATE REPORT
# =========================================================

async def create_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Starts report creation.
    """

    context.user_data.clear()

    await update.message.reply_text(
        "Enter the scammer's Telegram username or user ID.\n\n"
        "Example: @username"
    )

    return USERNAME


# =========================================================
# USERNAME STEP
# =========================================================

async def receive_username(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Receives and validates Telegram username/link/user ID.
    """

    raw_value = update.message.text.strip()

    target = normalize_telegram_target(raw_value)

    if target is None:
        await update.message.reply_text(
            "❌ Invalid Telegram username.\n\n"
            "Send:\n"
            "@username\n"
            "username\n"
            "t.me/username\n"
            "or Telegram user ID."
        )

        return USERNAME

    context.user_data["target_type"] = target["type"]
    context.user_data["target_value"] = target["value"]
    context.user_data["target_username"] = target["username"]

    await update.message.reply_text(
        "Enter the deal value:"
    )

    return AMOUNT


# =========================================================
# AMOUNT STEP
# =========================================================

async def receive_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Receives deal amount.
    """

    amount = clean_amount(update.message.text)

    if not amount:
        await update.message.reply_text(
            "❌ Keep the deal value short.\n"
            "Example: $100"
        )

        return AMOUNT

    context.user_data["amount"] = amount

    await update.message.reply_text(
        "Send a short explanation of the scam:"
    )

    return SUMMARY


# =========================================================
# SUMMARY STEP
# =========================================================

async def receive_summary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Receives short scam summary.
    """

    summary = clean_summary(update.message.text)

    if not summary:
        await update.message.reply_text(
            "❌ Keep the explanation short.\n"
            "Maximum 250 characters."
        )

        return SUMMARY

    context.user_data["summary"] = summary

    await update.message.reply_text(
        "Send the PRIVATE CHANNEL invite link containing the proofs:"
    )

    return PROOF_LINK


# =========================================================
# PROOF LINK STEP
# =========================================================

async def receive_proof_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Receives proof channel invite link.
    """

    proof_link = normalize_proof_link(
        update.message.text
    )

    if not proof_link:
        await update.message.reply_text(
            "❌ Invalid private channel link.\n\n"
            "Send a link like:\n"
            "https://t.me/+XXXXXXXX"
        )

        return PROOF_LINK

    context.user_data["proof_link"] = proof_link

    # Reporter information
    reporter = update.effective_user

    context.user_data["reporter_id"] = reporter.id
    context.user_data["reporter_name"] = (
        reporter.full_name or "Unknown"
    )
    context.user_data["reporter_username"] = (
        reporter.username
    )

    await submit_report(
        update,
        context,
    )

    return ConversationHandler.END


# =========================================================
# SUBMIT REPORT TO ADMIN
# =========================================================

async def submit_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Sends completed report to admin review chat.
    """

    global report_counter

    admin_chat_id = get_admin_chat_id()

    if not admin_chat_id:
        await update.message.reply_text(
            "❌ Bot configuration error.\n"
            "ADMIN_CHAT_ID is missing."
        )

        logger.error(
            "ADMIN_CHAT_ID environment variable is missing."
        )

        return

    report_counter += 1

    report_id = (
        f"{update.effective_user.id}_"
        f"{update.effective_message.message_id}_"
        f"{report_counter}"
    )

    report = {
        "report_id": report_id,

        "target_type":
            context.user_data.get("target_type"),

        "target_value":
            context.user_data.get("target_value"),

        "target_username":
            context.user_data.get("target_username"),

        "amount":
            context.user_data.get("amount"),

        "summary":
            context.user_data.get("summary"),

        "proof_link":
            context.user_data.get("proof_link"),

        "reporter_id":
            context.user_data.get("reporter_id"),

        "reporter_name":
            context.user_data.get("reporter_name"),

        "reporter_username":
            context.user_data.get("reporter_username"),

        "status": "pending",
    }

    pending_reports[report_id] = report

    reporter_username = report.get(
        "reporter_username"
    )

    if reporter_username:
        reporter_display = (
            f"@{escape(reporter_username)}"
        )
    else:
        reporter_display = escape(
            report.get("reporter_name", "Unknown")
        )

    admin_text = (
        "🚨 <b>NEW REPORT</b>\n\n"

        f"👤 <b>User:</b> "
        f"{escape(str(report['target_value']))}\n"

        f"💰 <b>Deal:</b> "
        f"{escape(str(report['amount']))}\n"

        f"📝 <b>Summary:</b> "
        f"{escape(str(report['summary']))}\n\n"

        f"📨 <b>Reporter:</b> "
        f"{reporter_display}\n"

        f"🆔 <b>Reporter ID:</b> "
        f"<code>{report['reporter_id']}</code>"
    )

    buttons = []

    profile_url = build_profile_url(report)

    first_row = []

    if profile_url:
        first_row.append(
            InlineKeyboardButton(
                "View Profile",
                url=profile_url,
            )
        )

    first_row.append(
        InlineKeyboardButton(
            "View Proofs",
            url=report["proof_link"],
        )
    )

    buttons.append(first_row)

    buttons.append(
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"approve:{report_id}",
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"reject:{report_id}",
            ),
        ]
    )

    try:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                buttons
            ),
            disable_web_page_preview=True,
        )

    except Exception as error:
        logger.exception(
            "Failed to send report to admin: %s",
            error,
        )

        pending_reports.pop(
            report_id,
            None,
        )

        await update.message.reply_text(
            "❌ Could not submit the report.\n"
            "Please try again later."
        )

        return

    await update.message.reply_text(
        "✅ Report submitted for review.",
        reply_markup=main_menu_keyboard(),
    )

    context.user_data.clear()


# =========================================================
# APPROVE / REJECT CALLBACK
# =========================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Handles admin approve/reject buttons.
    """

    query = update.callback_query

    await query.answer()

    try:
        action, report_id = (
            query.data.split(":", 1)
        )
    except ValueError:
        await query.answer(
            "Invalid action.",
            show_alert=True,
        )

        return

    report = pending_reports.get(
        report_id
    )

    if not report:
        await query.answer(
            "This report is no longer available.",
            show_alert=True,
        )

        return

    if report.get("status") != "pending":
        await query.answer(
            "This report was already reviewed.",
            show_alert=True,
        )

        return

    if action == "approve":
        await approve_report(
            query,
            context,
            report,
        )

    elif action == "reject":
        await reject_report(
            query,
            context,
            report,
        )


# =========================================================
# APPROVE REPORT
# =========================================================

async def approve_report(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    report,
):
    """
    Publishes approved scam report.
    """

    report["status"] = "approved"

    target = escape(
        str(report["target_value"])
    )

    amount = escape(
        str(report["amount"])
    )

    summary = escape(
        str(report["summary"])
    )

    caption = (
        f"❌ User {target} has been marked "
        f"as a scammer.\n\n"

        f"💰 <b>Deal:</b> {amount}\n"
        f"📝 <b>{summary}</b>"
    )

    buttons = []

    profile_url = build_profile_url(report)

    button_row = []

    if profile_url:
        button_row.append(
            InlineKeyboardButton(
                "View Profile ↗",
                url=profile_url,
            )
        )

    button_row.append(
        InlineKeyboardButton(
            "View Proofs ↗",
            url=report["proof_link"],
        )
    )

    buttons.append(button_row)

    markup = InlineKeyboardMarkup(
        buttons
    )

    try:

        # -------------------------------------
        # If banner URL exists
        # -------------------------------------

        if SCAM_BANNER_URL:

            await context.bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=SCAM_BANNER_URL,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )

        # -------------------------------------
        # If no banner configured
        # -------------------------------------

        else:

            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
                disable_web_page_preview=True,
            )

    except Exception as error:

        report["status"] = "pending"

        logger.exception(
            "Failed to publish approved report: %s",
            error,
        )

        await query.answer(
            "Could not publish the report. "
            "Check bot channel permissions.",
            show_alert=True,
        )

        return

    # -----------------------------------------
    # Notify reporter
    # -----------------------------------------

    try:
        await context.bot.send_message(
            chat_id=report["reporter_id"],
            text=(
                "✅ Your report was approved "
                "and published."
            ),
        )

    except Exception:
        pass

    # -----------------------------------------
    # Update admin review message
    # -----------------------------------------

    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Approved",
                            callback_data=(
                                f"done:{report['report_id']}"
                            ),
                        )
                    ]
                ]
            )
        )

    except BadRequest:
        pass


# =========================================================
# REJECT REPORT
# =========================================================

async def reject_report(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    report,
):
    """
    Rejects report.
    """

    report["status"] = "rejected"

    try:
        await context.bot.send_message(
            chat_id=report["reporter_id"],
            text=(
                "❌ Your report was rejected "
                "after review."
            ),
        )

    except Exception:
        pass

    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "❌ Rejected",
                            callback_data=(
                                f"done:{report['report_id']}"
                            ),
                        )
                    ]
                ]
            )
        )

    except BadRequest:
        pass


# =========================================================
# CANCEL
# =========================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Cancels report creation.
    """

    context.user_data.clear()

    await update.message.reply_text(
        "Report cancelled.",
        reply_markup=main_menu_keyboard(),
    )

    return ConversationHandler.END


# =========================================================
# UNKNOWN MESSAGE
# =========================================================

async def unknown_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Default response outside conversation.
    """

    await update.message.reply_text(
        "Use the menu below.",
        reply_markup=main_menu_keyboard(),
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Logs unexpected errors.
    """

    logger.exception(
        "Unhandled exception:",
        exc_info=context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():
    """
    Starts the bot.
    """

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
        )

    if not ADMIN_CHAT_ID_RAW:
        raise RuntimeError(
            "ADMIN_CHAT_ID environment variable is missing."
        )

    logger.info(
        "Starting AVOID REPORTS bot..."
    )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # -----------------------------------------
    # Conversation
    # -----------------------------------------

    conversation = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"(?i)^Create Report$"
                ),
                create_report,
            )
        ],

        states={

            USERNAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_username,
                )
            ],

            AMOUNT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_amount,
                )
            ],

            SUMMARY: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_summary,
                )
            ],

            PROOF_LINK: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_proof_link,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            )
        ],

        allow_reentry=True,
    )

    # -----------------------------------------
    # Handlers
    # -----------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "cancel",
            cancel,
        )
    )

    application.add_handler(
        conversation
    )

    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(approve|reject):",
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            unknown_message,
        )
    )

    application.add_error_handler(
        error_handler
    )

    # -----------------------------------------
    # Start polling
    # -----------------------------------------

    logger.info(
        "Bot polling started."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
