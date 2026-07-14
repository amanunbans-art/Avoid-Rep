import os
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = "8894281974:AAF3qi9-AnGWos_u8kcMTxk-pUaLA1x2qnk"
ADMIN_CHANNEL = -100xxxxxxxxxx # Yahan apni channel ID daalein

USERNAME, AMOUNT, SUMMARY, PROOF_LINK = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu = ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True)
    await update.message.reply_text("Welcome to @AvoidRepBot\n\nA specialized platform for reporting scammers.", reply_markup=menu)
    return ConversationHandler.END

async def ask_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter the scammer's username with (@) included [Example: @username].", reply_markup=ReplyKeyboardRemove())
    return USERNAME

async def ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['uname'] = update.message.text
    await update.message.reply_text("Enter the deal value:")
    return AMOUNT

async def ask_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['amt'] = update.message.text
    await update.message.reply_text("Send a short explanation about the scam. Keep it brief:")
    return SUMMARY

async def finish_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['summ'] = update.message.text
    await update.message.reply_text("Attach proof below, please send the PRIVATE CHANNEL invite link here.")
    return PROOF_LINK

async def submit_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    # Data summary
    msg = (f"🚨 **New Report**\n\n"
           f"👤 **Scammer:** {context.user_data['uname']}\n"
           f"💰 **Value:** {context.user_data['amt']}\n"
           f"📝 **Summary:** {context.user_data['summ']}\n"
           f"🔗 **Proof Link:** {link}")
    
    await context.bot.send_message(chat_id=ADMIN_CHANNEL, text=msg)
    await update.message.reply_text("✅ Report submitted! Our team will review it shortly.", reply_markup=ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True))
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Create Report$'), ask_username)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_amount)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_summary)],
            SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_report)],
            PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, submit_to_admin)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    
    # Render bypass
    Thread(target=lambda: HTTPServer(("", int(os.environ.get("PORT", 8080))), SimpleHTTPRequestHandler).serve_forever(), daemon=True).start()
    app.run_polling()

if __name__ == '__main__':
    main()
