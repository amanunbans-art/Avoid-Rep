import os
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters

# Aapka token yahan set hai
BOT_TOKEN = "8894281974:AAF3qi9-AnGWos_u8kcMTxk-pUaLA1x2qnk"

USERNAME, AMOUNT = range(2)

def get_menu():
    return ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True)

async def start(update: Update, context):
    txt = "Welcome to Avoid Report Bot!\n\nUse the button below to start a report."
    await update.message.reply_text(txt, reply_markup=get_menu())
    return ConversationHandler.END

async def report_start(update: Update, context):
    await update.message.reply_text("Enter the scammer's username:")
    return USERNAME

async def process_username(update: Update, context):
    context.user_data['uname'] = update.message.text
    await update.message.reply_text("Enter amount scammed:")
    return AMOUNT

async def process_amount(update: Update, context):
    amt = update.message.text
    uname = context.user_data.get('uname')
    await update.message.reply_text(f"✅ Report received!\n\nScammer: {uname}\nAmount: {amt}")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Create Report$'), report_start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_username)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_amount)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    # Render ka port bypass
    def run_port():
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("", port), SimpleHTTPRequestHandler)
        server.serve_forever()
    Thread(target=run_port, daemon=True).start()

    print("🚀 Bot running...")
    app.run_polling(close_loop=False)

if __name__ == '__main__':
    main()
