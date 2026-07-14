import os
import logging
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# --- CONFIG ---
# 1. Yahan apna Token rakhein
BOT_TOKEN = "8894281974:AAF3qi9-AnGWos_u8kcMTxk-pUaLA1x2qnk"
# 2. Yahan apni Channel ID rakhein (zaroor quotes mein)
ADMIN_CHANNEL = "-1001234567890" 

# States
USERNAME, AMOUNT, SUMMARY, PROOF_LINK = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu = ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True)
    await update.message.reply_text("Welcome to @AvoidRepBot\n\nA specialized platform to report scammers.", reply_markup=menu)
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
    uname = context.user_data.get('uname')
    amt = context.user_data.get('amt')
    summ = context.user_data.get('summ')
    
    # Admin Channel par report bhejna
    msg = (f"🚨 **New Report Received**\n\n"
           f"👤 **Scammer:** {uname}\n"
           f"💰 **Value:** {amt}\n"
           f"📝 **Summary:** {summ}\n"
           f"🔗 **Proof Link:** {link}")
    
    try:
        await context.bot.send_message(chat_id=ADMIN_CHANNEL, text=msg)
        await update.message.reply_text("✅ Report successfully submitted to admin!", reply_markup=ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True))
    except Exception as e:
        await update.message.reply_text("❌ Error sending report to admin. Please check bot permissions in the channel.")
    
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
    
    # Port setup
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: HTTPServer(("", port), SimpleHTTPRequestHandler).serve_forever(), daemon=True).start()
    
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
