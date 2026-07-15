import asyncio
import html
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@avoidrep").strip()

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().lstrip("-").isdigit()
}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

if not ADMIN_CHAT_ID_RAW.lstrip("-").isdigit():
    raise RuntimeError("ADMIN_CHAT_ID environment variable is missing or invalid.")

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_RAW)

if not CHANNEL_USERNAME.startswith("@"):
    CHANNEL_USERNAME = "@" + CHANNEL_USERNAME

CHANNEL_LINK = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "avoid_reports.db"
BANNER_PATH = BASE_DIR / "banner.jpg"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("avoid-reports")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


# ============================================================
# DATABASE
# ============================================================

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TEXT NOT NULL,
                is_banned INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT UNIQUE,
                reporter_id INTEGER NOT NULL,
                reporter_username TEXT,
                platform TEXT NOT NULL,
                accused TEXT NOT NULL,
                deal_value TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence_link TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                rejection_reason TEXT,
                admin_id INTEGER,
                admin_message_id INTEGER,
                channel_message_id INTEGER,
                created_at TEXT NOT NULL,
                reviewed_at TEXT
            )
            """
        )

        conn.commit()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def add_or_update_user(user):
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO users (
                telegram_id,
                username,
                first_name,
                joined_at,
                is_banned
            )
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (
                user.id,
                user.username,
                user.first_name,
                now_iso(),
            ),
        )
        conn.commit()


def is_user_banned(user_id: int) -> bool:
    with db_connect() as conn:
        row = conn.execute(
            "SELECT is_banned FROM users WHERE telegram_id = ?",
            (user_id,),
        ).fetchone()

        return bool(row and row["is_banned"])


def set_user_banned(user_id: int, banned: bool):
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO users (
                telegram_id,
                username,
                first_name,
                joined_at,
                is_banned
            )
            VALUES (?, NULL, NULL, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                is_banned = excluded.is_banned
            """,
            (
                user_id,
                now_iso(),
                1 if banned else 0,
            ),
        )
        conn.commit()


def create_report(
    reporter_id: int,
    reporter_username: str | None,
    platform: str,
    accused: str,
    deal_value: str,
    description: str,
    evidence_link: str,
):
    with db_connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reports (
                reporter_id,
                reporter_username,
                platform,
                accused,
                deal_value,
                description,
                evidence_link,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                reporter_id,
                reporter_username,
                platform,
                accused,
                deal_value,
                description,
                evidence_link,
                now_iso(),
            ),
        )

        database_id = cursor.lastrowid
        report_id = f"AVD{database_id:04d}"

        conn.execute(
            """
            UPDATE reports
            SET report_id = ?
            WHERE id = ?
            """,
            (
                report_id,
                database_id,
            ),
        )

        conn.commit()

    return report_id


def get_report(report_id: str):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM reports
            WHERE report_id = ?
            """,
            (report_id,),
        ).fetchone()


def set_admin_message_id(report_id: str, message_id: int):
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE reports
            SET admin_message_id = ?
            WHERE report_id = ?
            """,
            (
                message_id,
                report_id,
            ),
        )
        conn.commit()


def approve_report_db(
    report_id: str,
    admin_id: int,
    channel_message_id: int,
):
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE reports
            SET
                status = 'approved',
                admin_id = ?,
                channel_message_id = ?,
                reviewed_at = ?
            WHERE report_id = ?
              AND status = 'pending'
            """,
            (
                admin_id,
                channel_message_id,
                now_iso(),
                report_id,
            ),
        )
        conn.commit()


def reject_report_db(
    report_id: str,
    admin_id: int,
    reason: str,
):
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE reports
            SET
                status = 'rejected',
                admin_id = ?,
                rejection_reason = ?,
                reviewed_at = ?
            WHERE report_id = ?
              AND status = 'pending'
            """,
            (
                admin_id,
                reason,
                now_iso(),
                report_id,
            ),
        )
        conn.commit()


def get_user_reports(user_id: int):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM reports
            WHERE reporter_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()


def search_approved_reports(query: str):
    normalized = query.strip().lower()

    with db_connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM reports
            WHERE status = 'approved'
              AND LOWER(accused) = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (normalized,),
        ).fetchall()


# ============================================================
# STATES
# ============================================================

class ReportStates(StatesGroup):
    choosing_platform = State()
    waiting_accused = State()
    waiting_amount = State()
    waiting_description = State()
    waiting_evidence = State()
    reviewing = State()


class SearchStates(StatesGroup):
    waiting_query = State()


class AdminStates(StatesGroup):
    waiting_rejection_reason = State()


# ============================================================
# HELPERS
# ============================================================

def esc(value) -> str:
    return html.escape(str(value or ""))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def valid_accused(value: str) -> bool:
    value = value.strip()

    if re.fullmatch(r"@[A-Za-z0-9_]{5,32}", value):
        return True

    if value.isdigit() and 5 <= len(value) <= 20:
        return True

    return False


def valid_telegram_link(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"https://t\.me/[A-Za-z0-9_+\-/]+",
            value.strip(),
        )
    )


def profile_url(accused: str) -> str | None:
    accused = accused.strip()

    if accused.startswith("@"):
        return f"https://t.me/{accused[1:]}"

    return None


def main_menu():
    kb = InlineKeyboardBuilder()

    kb.button(
        text="🚨 Report a Scammer",
        callback_data="create_report",
    )

    kb.button(
        text="🔍 Search Reports",
        callback_data="search_reports",
    )

    kb.button(
        text="📋 My Reports",
        callback_data="my_reports",
    )

    kb.row(
        InlineKeyboardButton(
            text=f"📢 Join {CHANNEL_USERNAME}",
            url=CHANNEL_LINK,
        )
    )

    kb.adjust(1)

    return kb.as_markup()


def cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_report",
                )
            ]
        ]
    )


def platform_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✈️ Telegram",
                    callback_data="platform:Telegram",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📸 Instagram",
                    callback_data="platform:Instagram",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Other",
                    callback_data="platform:Other",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_report",
                )
            ],
        ]
    )


def review_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Submit Report",
                    callback_data="submit_report",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Start Again",
                    callback_data="create_report",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_report",
                )
            ],
        ]
    )


def admin_report_keyboard(report_id: str, accused: str, evidence: str):
    rows = [
        [
            InlineKeyboardButton(
                text="✅ Approve",
                callback_data=f"approve:{report_id}",
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data=f"reject:{report_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📂 View Proofs",
                url=evidence,
            )
        ],
    ]

    url = profile_url(accused)

    if url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="👤 View Profile",
                    url=url,
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def public_post_keyboard(accused: str, evidence: str):
    row = []

    url = profile_url(accused)

    if url:
        row.append(
            InlineKeyboardButton(
                text="👤 View Profile",
                url=url,
            )
        )

    row.append(
        InlineKeyboardButton(
            text="📂 View Proofs",
            url=evidence,
        )
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[row]
    )


def status_text(status: str) -> str:
    mapping = {
        "pending": "⏳ Pending Review",
        "approved": "✅ Approved",
        "rejected": "❌ Rejected",
    }

    return mapping.get(status, status)


async def safe_send_message(chat_id: int, text: str, **kwargs):
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            **kwargs,
        )

    except (TelegramForbiddenError, TelegramBadRequest) as error:
        logger.warning(
            "Could not send message to %s: %s",
            chat_id,
            error,
        )

        return None


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    add_or_update_user(message.from_user)
    await state.clear()

    text = (
        "<b>🛡️ WELCOME TO AVOID REPORTS</b>\n\n"
        "A community-driven reporting platform designed to help "
        "users submit reports related to potentially fraudulent deals.\n\n"
        "📋 Every submitted report is manually reviewed by the "
        "moderation team before publication.\n\n"
        "⚠️ False, incomplete, misleading, or manipulated reports "
        "may be rejected.\n\n"
        "Choose an option below to continue.\n\n"
        f"🛡️ <b>{esc(CHANNEL_USERNAME)}</b>"
    )

    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.message.edit_text(
        "<b>🛡️ AVOID REPORTS</b>\n\n"
        "Choose an option below.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )

    await callback.answer()


# ============================================================
# CREATE REPORT
# ============================================================

@router.callback_query(F.data == "create_report")
async def create_report_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    add_or_update_user(callback.from_user)

    if is_user_banned(callback.from_user.id):
        await callback.answer(
            "Your reporting access is restricted.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(ReportStates.choosing_platform)

    await callback.message.edit_text(
        "<b>🚨 CREATE A NEW REPORT</b>\n\n"
        "Please select the platform where the incident occurred.",
        parse_mode=ParseMode.HTML,
        reply_markup=platform_keyboard(),
    )

    await callback.answer()


@router.callback_query(
    ReportStates.choosing_platform,
    F.data.startswith("platform:"),
)
async def platform_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    platform = callback.data.split(":", 1)[1]

    await state.update_data(platform=platform)
    await state.set_state(ReportStates.waiting_accused)

    await callback.message.edit_text(
        "<b>👤 REPORTED ACCOUNT INFORMATION</b>\n\n"
        "Please send the username of the account you want to report.\n\n"
        "Example:\n"
        "<code>@username</code>\n\n"
        "For Telegram reports, you may also send a numeric Telegram "
        "User ID if the account has no username.\n\n"
        "⚠️ Make sure you are reporting the correct account.",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard(),
    )

    await callback.answer()


@router.message(ReportStates.waiting_accused)
async def accused_handler(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Please send a username or numeric User ID."
        )
        return

    accused = message.text.strip()

    if not valid_accused(accused):
        await message.answer(
            "❌ Invalid username or User ID.\n\n"
            "Send a username like:\n"
            "<code>@username</code>\n\n"
            "Or a numeric Telegram User ID.",
            parse_mode=ParseMode.HTML,
        )
        return

    await state.update_data(accused=accused)
    await state.set_state(ReportStates.waiting_amount)

    await message.answer(
        "<b>💰 DEAL VALUE</b>\n\n"
        "Enter the total amount involved in the deal.\n\n"
        "Examples:\n"
        "<code>$100</code>\n"
        "<code>₹5,000</code>\n"
        "<code>100 USDT</code>\n\n"
        "If no money was involved, send:\n"
        "<code>0</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard(),
    )


@router.message(ReportStates.waiting_amount)
async def amount_handler(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Please enter the deal value as text."
        )
        return

    amount = message.text.strip()

    if len(amount) > 100:
        await message.answer(
            "❌ Deal value is too long."
        )
        return

    await state.update_data(deal_value=amount)
    await state.set_state(ReportStates.waiting_description)

    await message.answer(
        "<b>📝 INCIDENT DETAILS</b>\n\n"
        "Briefly explain what happened.\n\n"
        "Please include:\n\n"
        "• What the deal was for\n"
        "• What you paid, sent, or provided\n"
        "• What the other party agreed to do\n"
        "• What went wrong\n\n"
        "Keep your explanation clear and factual.",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard(),
    )


@router.message(ReportStates.waiting_description)
async def description_handler(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Please send the incident description as text."
        )
        return

    description = message.text.strip()

    if len(description) < 20:
        await message.answer(
            "❌ Description is too short. Please provide at least "
            "20 characters."
        )
        return

    if len(description) > 3000:
        await message.answer(
            "❌ Description is too long. Maximum is 3000 characters."
        )
        return

    await state.update_data(description=description)
    await state.set_state(ReportStates.waiting_evidence)

    await message.answer(
        "<b>📂 SUBMIT EVIDENCE</b>\n\n"
        "Create a Telegram channel containing all relevant evidence "
        "and send the channel link here.\n\n"
        "Your evidence should preferably include:\n\n"
        "• Full conversation screenshots\n"
        "• Screen recording of the conversation\n"
        "• Reported account's profile\n"
        "• Username and User ID, if available\n"
        "• Payment or transaction proof\n"
        "• Other relevant evidence\n\n"
        "Example:\n"
        "<code>https://t.me/+xxxxxxxx</code>\n\n"
        "⚠️ Incomplete or manipulated evidence may result in rejection.",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard(),
    )


@router.message(ReportStates.waiting_evidence)
async def evidence_handler(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Please send the Telegram evidence channel link."
        )
        return

    evidence = message.text.strip()

    if not valid_telegram_link(evidence):
        await message.answer(
            "❌ Invalid Telegram link.\n\n"
            "The link must begin with:\n"
            "<code>https://t.me/</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    await state.update_data(evidence_link=evidence)

    data = await state.get_data()

    preview = (
        "<b>🔎 REVIEW YOUR REPORT</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "<b>🚨 REPORT DETAILS</b>\n\n"
        f"📱 <b>Platform:</b> {esc(data['platform'])}\n"
        f"👤 <b>Reported Account:</b> {esc(data['accused'])}\n"
        f"💰 <b>Deal Value:</b> {esc(data['deal_value'])}\n\n"
        "<b>📝 Incident Details:</b>\n\n"
        f"{esc(data['description'])}\n\n"
        f"📂 <b>Evidence:</b>\n{esc(data['evidence_link'])}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ By submitting this report, you confirm that the information "
        "provided is accurate to the best of your knowledge."
    )

    await state.set_state(ReportStates.reviewing)

    await message.answer(
        preview,
        parse_mode=ParseMode.HTML,
        reply_markup=review_keyboard(),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "cancel_report")
async def cancel_report_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.message.edit_text(
        "<b>❌ REPORT CANCELLED</b>\n\n"
        "No report was submitted.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )

    await callback.answer()


# ============================================================
# SUBMIT REPORT
# ============================================================

@router.callback_query(
    ReportStates.reviewing,
    F.data == "submit_report",
)
async def submit_report_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if is_user_banned(callback.from_user.id):
        await callback.answer(
            "Your reporting access is restricted.",
            show_alert=True,
        )
        return

    data = await state.get_data()

    required = {
        "platform",
        "accused",
        "deal_value",
        "description",
        "evidence_link",
    }

    if not required.issubset(data):
        await callback.answer(
            "Report data is incomplete. Please start again.",
            show_alert=True,
        )
        return

    report_id = create_report(
        reporter_id=callback.from_user.id,
        reporter_username=callback.from_user.username,
        platform=data["platform"],
        accused=data["accused"],
        deal_value=data["deal_value"],
        description=data["description"],
        evidence_link=data["evidence_link"],
    )

    reporter_username = (
        f"@{callback.from_user.username}"
        if callback.from_user.username
        else "No username"
    )

    admin_text = (
        "<b>🚨 NEW REPORT RECEIVED</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>Report ID:</b> #{esc(report_id)}\n"
        "⏳ <b>Status:</b> PENDING REVIEW\n\n"
        "<b>👤 REPORTER</b>\n\n"
        f"Username: {esc(reporter_username)}\n"
        f"User ID: <code>{callback.from_user.id}</code>\n\n"
        "<b>🚨 REPORTED ACCOUNT</b>\n\n"
        f"Platform: {esc(data['platform'])}\n"
        f"Account: {esc(data['accused'])}\n\n"
        "<b>💰 DEAL VALUE</b>\n\n"
        f"{esc(data['deal_value'])}\n\n"
        "<b>📝 INCIDENT DETAILS</b>\n\n"
        f"{esc(data['description'])}\n\n"
        "<b>📂 EVIDENCE</b>\n\n"
        f"{esc(data['evidence_link'])}\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    admin_message = await safe_send_message(
        ADMIN_CHAT_ID,
        admin_text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_report_keyboard(
            report_id,
            data["accused"],
            data["evidence_link"],
        ),
        disable_web_page_preview=True,
    )

    if admin_message:
        set_admin_message_id(
            report_id,
            admin_message.message_id,
        )

    await state.clear()

    await callback.message.edit_text(
        "<b>✅ REPORT SUBMITTED SUCCESSFULLY</b>\n\n"
        "Your report has been sent to the AVOID REPORTS moderation "
        "team for manual review.\n\n"
        f"🆔 <b>Report ID:</b> #{esc(report_id)}\n"
        "⏳ <b>Status:</b> Pending Review\n\n"
        "You will receive an update after your report is reviewed.\n\n"
        "⚠️ False reports or manipulated evidence may result in "
        "reporting restrictions.\n\n"
        f"🛡️ <b>{esc(CHANNEL_USERNAME)}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )

    await callback.answer("Report submitted.")


# ============================================================
# ADMIN APPROVE
# ============================================================

@router.callback_query(F.data.startswith("approve:"))
async def approve_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "You are not authorized.",
            show_alert=True,
        )
        return

    report_id = callback.data.split(":", 1)[1]
    report = get_report(report_id)

    if not report:
        await callback.answer(
            "Report not found.",
            show_alert=True,
        )
        return

    if report["status"] != "pending":
        await callback.answer(
            f"This report is already {report['status']}.",
            show_alert=True,
        )
        return

    caption = (
        "<b>🚨 COMMUNITY SAFETY REPORT</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>REPORT ID</b>\n"
        f"#{esc(report['report_id'])}\n\n"
        f"👤 <b>REPORTED ACCOUNT</b>\n"
        f"{esc(report['accused'])}\n\n"
        f"📱 <b>PLATFORM</b>\n"
        f"{esc(report['platform'])}\n\n"
        f"💰 <b>REPORTED DEAL VALUE</b>\n"
        f"{esc(report['deal_value'])}\n\n"
        f"📝 <b>INCIDENT SUMMARY</b>\n\n"
        f"{esc(report['description'])}\n\n"
        "📂 <b>EVIDENCE</b>\n\n"
        "Supporting evidence is available through the button below.\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ This post records a community-submitted report reviewed "
        "by the moderation team based on the evidence provided. "
        "Users should review the available evidence and make their "
        "own assessment before dealing.\n\n"
        f"🛡️ <b>AVOID REPORTS</b>\n"
        f"{esc(CHANNEL_USERNAME)}"
    )

    try:
        if BANNER_PATH.exists():
            sent_post = await bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=FSInputFile(BANNER_PATH),
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=public_post_keyboard(
                    report["accused"],
                    report["evidence_link"],
                ),
            )

        else:
            sent_post = await bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=public_post_keyboard(
                    report["accused"],
                    report["evidence_link"],
                ),
                disable_web_page_preview=True,
            )

    except Exception as error:
        logger.exception(
            "Could not publish report %s",
            report_id,
        )

        await callback.answer(
            f"Publishing failed: {str(error)[:150]}",
            show_alert=True,
        )
        return

    approve_report_db(
        report_id=report_id,
        admin_id=callback.from_user.id,
        channel_message_id=sent_post.message_id,
    )

    try:
        await callback.message.edit_text(
            callback.message.html_text
            + "\n\n"
            + "━━━━━━━━━━━━━━━━━━\n\n"
            + "✅ <b>APPROVED & PUBLISHED</b>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

    except TelegramBadRequest:
        pass

    channel_post_url = (
        f"{CHANNEL_LINK}/{sent_post.message_id}"
    )

    await safe_send_message(
        report["reporter_id"],
        "<b>✅ YOUR REPORT HAS BEEN APPROVED</b>\n\n"
        f"🆔 <b>Report ID:</b> #{esc(report_id)}\n\n"
        "Your report has been reviewed and approved by the "
        "AVOID REPORTS moderation team.\n\n"
        f"The report has been published to {esc(CHANNEL_USERNAME)}.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📢 View Published Report",
                        url=channel_post_url,
                    )
                ]
            ]
        ),
    )

    await callback.answer(
        "Approved and published.",
        show_alert=True,
    )


# ============================================================
# ADMIN REJECT
# ============================================================

@router.callback_query(F.data.startswith("reject:"))
async def reject_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "You are not authorized.",
            show_alert=True,
        )
        return

    report_id = callback.data.split(":", 1)[1]
    report = get_report(report_id)

    if not report:
        await callback.answer(
            "Report not found.",
            show_alert=True,
        )
        return

    if report["status"] != "pending":
        await callback.answer(
            f"This report is already {report['status']}.",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminStates.waiting_rejection_reason
    )

    await state.update_data(
        rejection_report_id=report_id
    )

    await callback.message.answer(
        "<b>❌ REJECT REPORT</b>\n\n"
        f"Report: <b>#{esc(report_id)}</b>\n\n"
        "Send the rejection reason now.\n\n"
        "Example:\n"
        "<i>Insufficient or incomplete evidence.</i>",
        parse_mode=ParseMode.HTML,
    )

    await callback.answer()


@router.message(AdminStates.waiting_rejection_reason)
async def rejection_reason_handler(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
        await message.answer(
            "Please send the rejection reason as text."
        )
        return

    reason = message.text.strip()

    if len(reason) < 3:
        await message.answer(
            "Rejection reason is too short."
        )
        return

    data = await state.get_data()
    report_id = data.get("rejection_report_id")

    report = get_report(report_id)

    if not report:
        await state.clear()

        await message.answer(
            "❌ Report not found."
        )
        return

    if report["status"] != "pending":
        await state.clear()

        await message.answer(
            f"Report is already {report['status']}."
        )
        return

    reject_report_db(
        report_id=report_id,
        admin_id=message.from_user.id,
        reason=reason,
    )

    await safe_send_message(
        report["reporter_id"],
        "<b>❌ REPORT REJECTED</b>\n\n"
        f"🆔 <b>Report ID:</b> #{esc(report_id)}\n\n"
        "Your report was reviewed but could not be approved.\n\n"
        "<b>Reason:</b>\n\n"
        f"{esc(reason)}\n\n"
        "You may submit a new report if you can provide complete "
        "and verifiable information or evidence.\n\n"
        f"🛡️ <b>{esc(CHANNEL_USERNAME)}</b>",
        parse_mode=ParseMode.HTML,
    )

    await state.clear()

    await message.answer(
        f"✅ Report #{esc(report_id)} rejected.",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# SEARCH REPORTS
# ============================================================

@router.callback_query(F.data == "search_reports")
async def search_reports_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()
    await state.set_state(SearchStates.waiting_query)

    await callback.message.edit_text(
        "<b>🔍 SEARCH REPORTS</b>\n\n"
        "Send an exact username or numeric User ID.\n\n"
        "Examples:\n"
        "<code>@username</code>\n"
        "<code>123456789</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏠 Main Menu",
                        callback_data="main_menu",
                    )
                ]
            ]
        ),
    )

    await callback.answer()


@router.message(SearchStates.waiting_query)
async def search_query_handler(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "Please send a username or User ID."
        )
        return

    query = message.text.strip()

    reports = search_approved_reports(query)

    await state.clear()

    if not reports:
        await message.answer(
            "<b>✅ NO APPROVED REPORT FOUND</b>\n\n"
            "No approved report was found for this username or "
            "User ID in the AVOID REPORTS database.\n\n"
            "⚠️ This does not guarantee that an account is trustworthy. "
            "Always verify independently before making a deal.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )
        return

    report_ids = "\n".join(
        f"• #{esc(report['report_id'])}"
        for report in reports
    )

    await message.answer(
        "<b>🚨 APPROVED REPORTS FOUND</b>\n\n"
        f"👤 <b>Account:</b> {esc(query)}\n"
        f"📊 <b>Approved Reports:</b> {len(reports)}\n\n"
        "<b>Report IDs:</b>\n"
        f"{report_ids}\n\n"
        "⚠️ Review available evidence before making your own decision.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )


# ============================================================
# MY REPORTS
# ============================================================

@router.callback_query(F.data == "my_reports")
async def my_reports_callback(callback: CallbackQuery):
    reports = get_user_reports(callback.from_user.id)

    if not reports:
        await callback.message.edit_text(
            "<b>📋 MY REPORTS</b>\n\n"
            "You have not submitted any reports yet.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )

        await callback.answer()
        return

    lines = []

    for index, report in enumerate(reports, start=1):
        lines.append(
            f"{index}. <b>#{esc(report['report_id'])}</b>\n"
            f"Account: {esc(report['accused'])}\n"
            f"Status: {status_text(report['status'])}"
        )

    await callback.message.edit_text(
        "<b>📋 MY REPORTS</b>\n\n"
        + "\n\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )

    await callback.answer()


# ============================================================
# ADMIN COMMANDS
# ============================================================

@router.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    with db_connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM reports"
        ).fetchone()["c"]

        pending = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM reports
            WHERE status = 'pending'
            """
        ).fetchone()["c"]

        approved = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM reports
            WHERE status = 'approved'
            """
        ).fetchone()["c"]

        rejected = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM reports
            WHERE status = 'rejected'
            """
        ).fetchone()["c"]

        users = conn.execute(
            "SELECT COUNT(*) AS c FROM users"
        ).fetchone()["c"]

    await message.answer(
        "<b>🛡️ AVOID REPORTS — ADMIN PANEL</b>\n\n"
        f"👥 Total Users: <b>{users}</b>\n\n"
        f"📋 Total Reports: <b>{total}</b>\n"
        f"⏳ Pending: <b>{pending}</b>\n"
        f"✅ Approved: <b>{approved}</b>\n"
        f"❌ Rejected: <b>{rejected}</b>",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("ban"))
async def ban_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "Usage:\n<code>/ban USER_ID</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    user_id = int(parts[1])

    set_user_banned(
        user_id,
        True,
    )

    await message.answer(
        f"🚫 User <code>{user_id}</code> has been banned "
        "from submitting reports.",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("unban"))
async def unban_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "Usage:\n<code>/unban USER_ID</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    user_id = int(parts[1])

    set_user_banned(
        user_id,
        False,
    )

    await message.answer(
        f"✅ User <code>{user_id}</code> has been unbanned.",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("chatid"))
async def chat_id_command(message: Message):
    await message.answer(
        f"Chat ID:\n<code>{message.chat.id}</code>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# START BOT
# ============================================================

async def main():
    init_db()

    logger.info("Starting AVOID REPORTS bot...")

    await bot.delete_webhook(
        drop_pending_updates=False
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Bot stopped.")
