import os
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = "8894281974:AAF3qi9-AnGWos_u8kcMTxk-pUaLA1x2qnk"
ADMIN_CHANNEL = "-1001234567890" # <-- APNI SAHI CHANNEL ID YAHAN DALO

USERNAME, AMOUNT, SUMMARY, PROOF_LINK = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu = ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True)
    await update.message.reply_text("Welcome to @AvoidRepBot\n\nReporting platform is ready.", reply_markup=menu)
    return ConversationHandler.END

async def ask_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter the scammer's username (with @):", reply_markup=ReplyKeyboardRemove())
    return USERNAME

async def ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['uname'] = update.message.text
    await update.message.reply_text("Enter the deal value (amount):")
    return AMOUNT

async def ask_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['amt'] = update.message.text
    await update.message.reply_text("Send a short explanation of the scam:")
    return SUMMARY

async def finish_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['summ'] = update.message.text
    await update.message.reply_text("Now, send the PRIVATE CHANNEL invite link containing the proofs:")
    return PROOF_LINK

async def submit_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    msg = (f"🚨 **New Scam Report**\n\n"
           f"👤 **Scammer:** {context.user_data['uname']}\n"
           f"💰 **Value:** {context.user_data['amt']}\n"
           f"📝 **Summary:** {context.user_data['summ']}\n"
           f"🔗 **Proof Link:** {link}")
    
    await context.bot.send_message(chat_id=ADMIN_CHANNEL, text=msg)
    await update.message.reply_text("✅ Report sent to admin!", reply_markup=ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True))
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Create Report$'), ask_username)],
        states={
            USERNAME: [MessageHandler(filters.TEXT, ask_amount)],
            AMOUNT: [MessageHandler(filters.TEXT, ask_summary)],
            SUMMARY: [MessageHandler(filters.TEXT, finish_report)],
            PROOF_LINK: [MessageHandler(filters.TEXT, submit_to_admin)]
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: HTTPServer(("", port), SimpleHTTPRequestHandler).serve_forever(), daemon=True).start()
    app.run_polling()

if __name__ == '__main__':
    main()
