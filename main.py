from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
import random, string

BOT_TOKEN, ADMIN_ID, PUBLIC_CHANNEL = "8894281974:AAF3", "YOUR_ADMIN_ID", "YOUR_CHANNEL"
USERNAME, AMOUNT, EXPLANATION, PROOF_LINK, CONFIRM = range(5)

def get_menu():
    return ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True)

async def start(update: Update, context):
    txt = "Welcome to @ControlFraudsBot\n\nA specialized platform..."
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Report", callback_data="rep")]]))
    await update.message.reply_text("✨ Main Menu", reply_markup=get_menu())
    return ConversationHandler.END

async def report(update: Update, context):
    await update.message.reply_text("Enter the scammer's username:")
    return USERNAME

async def process_username(update: Update, context):
    context.user_data['uname'] = update.message.text
    await update.message.reply_text("Enter amount scammed:")
    return AMOUNT

async def cancel(update: Update, context):
    await update.message.reply_text("Process cancelled.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("report", report)],
        states={USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_username)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    app.add_handler(CallbackQueryHandler(get_menu))

    # --- RENDER PORT BYPASS CODE START ---
    import os
    from threading import Thread
    from http.server import SimpleHTTPRequestHandler, HTTPServer

    def run_port():
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("", port), SimpleHTTPRequestHandler)
        server.serve_forever()

    Thread(target=run_port, daemon=True).start()
    # --- RENDER PORT BYPASS CODE END ---

    print("🚀 Bot running...")
    app.run_polling(close_loop=False)

if __name__ == '__main__':
    main()
