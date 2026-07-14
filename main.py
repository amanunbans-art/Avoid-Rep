from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
import random, string

BOT_TOKEN, ADMIN_ID, PUBLIC_CHANNEL = "8894281974:AAF3qi9-AnGWos_u8kcMTxk-pUaLA1x2qnk", 6557165360, "@avoidrep"
USERNAME, AMOUNT, EXPLANATION, PROOF_LINK, CONFIRM = range(5)

def get_menu(): 
    return ReplyKeyboardMarkup([['Create Report']], resize_keyboard=True)

async def start(u: Update, c):
    txt = "Welcome to @ControlFraudsBot\n\nA specialized platform committed to reporting scammers!\n\nAll reports are reviewed by mods before being published.\n\nNote: Your report will be rejected if you are not a member of @controlfrauds!\n\n⚡ Powered By: @AFFUX"
    await u.message.reply_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join @CONTROLFRAUDS ↗️", url="https://t.me/avoidrep")]]))
    await u.message.reply_text("✨ Main Menu", reply_markup=get_menu())

async def start_report(u: Update, c):
    await u.message.reply_text("Enter the scammer's username with (@) included [Example: @username]. If they have no username, send the user id of the scammer:")
    return USERNAME

async def get_username(u: Update, c):
    c.user_data['scammer'] = u.message.text
    await u.message.reply_text("Enter the deal value:")
    return AMOUNT

async def get_amount(u: Update, c):
    c.user_data['amount'] = u.message.text
    await u.message.reply_text("Send a short and straightforward explanation about the scam. Make it brief and short , don't send long paragraphs.")
    return EXPLANATION

async def get_explanation(u: Update, c):
    c.user_data['explain'] = u.message.text
    await u.message.reply_text("Attach proof below, please send the channel as a t.me link.\n\nIf you do not have that ready, make a PRIVATE CHANNEL (NOT A GROUP) with all proof (including a screen recording showing the FULL chat and the scammer's profile), and send the invite link here.")
    return PROOF_LINK

async def get_proof_link(u: Update, c):
    lnk = u.message.text
    if "t.me/" not in lnk:
        await u.message.reply_text("❌ Please send a valid Telegram link.")
        return PROOF_LINK
    c.user_data['proof'] = lnk
    cid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    c.user_data['cid'] = cid
    pvw = f"📝 **Review Report (Case: #{cid})**\n\n👤 **Scammer:** {c.user_data['scammer']}\n💸 **Loss:** {c.user_data['amount']}\n💬 **Info:** {c.user_data['explain']}\n🔗 **Proof:** {lnk}"
    await u.message.reply_text(pvw, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Submit Report 🚀", callback_data="sub_adm")]]))
    return CONFIRM

async def send_to_admin(u: Update, c):
    q = u.callback_query
    await q.answer()
    cid, sc, am, ex, pr = c.user_data['cid'], c.user_data['scammer'], c.user_data['amount'], c.user_data['explain'], c.user_data['proof']
    if not c.bot_data.get('cases'): 
        c.bot_data['cases'] = {}
    c.bot_data['cases'][cid] = {'scammer': sc, 'amount': am, 'explain': ex, 'proof': pr}
    adm_txt = f"⚡ **NEW CASE [#{cid}]**\n━━━━━━━━━━━━━\n👤 **Scammer:** `{sc}`\n💰 **Amount:** `{am}`\n💬 **Explanation:** {ex}\n━━━━━━━━━━━━━\n🛡️ **Reporter:** {q.from_user.mention_html()}"
    btns = [[InlineKeyboardButton("👁️ View Proofs Link", url=pr)], [InlineKeyboardButton("Accept ✅", callback_data=f"ok_{cid}"), InlineKeyboardButton("Reject ❌", callback_data=f"no_{cid}")]]
    await c.bot.send_message(chat_id=ADMIN_ID, text=adm_txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
    await q.edit_message_text("✅ **Report sent!**", reply_markup=get_menu())
    return ConversationHandler.END

async def admin_buttons_handler(u: Update, c):
    q = u.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("❌ Access Denied!", show_alert=True)
        return
    await q.answer()
    act, cid = q.data.split("_")
    if act == "ok":
        data = c.bot_data.get('cases', {}).get(cid)
        if data:
            sc, am, ex, pr = data['scammer'], data['amount'], data['explain'], data['proof']
            p_url = f"https://t.me/{sc.replace('@', '')}" if sc.startswith("@") else f"https://t.me/{sc}"
            pub_txt = f"🚨 **SCAMMER ALERT [#{cid}]** 🚨\n━━━━━━━━━━━━━━━━━━━━\n❌ **User {sc} has been marked as a scammer.**\n\n💸 **Loss Amount:** {am}\n💬 **Description:** {ex}\n━━━━━━━━━━━━━━━━━━━━\n⚠️ **Is bande se savdhan rahein, yeh fraud kar raha hai!**"
            p_btns = [[InlineKeyboardButton("View Profile ↗️", url=p_url), InlineKeyboardButton("View Proofs ↗️", url=pr)]]
            await c.bot.send_message(chat_id=PUBLIC_CHANNEL, text=pub_txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(p_btns), disable_web_page_preview=True)
            await q.edit_message_text(f"🟢 **Case #{cid} APPROVED!**")
    else:
        await q.edit_message_text(f"🔴 **Case #{cid} REJECTED**.")
    if cid in c.bot_data.get('cases', {}): 
        del c.bot_data['cases'][cid]

async def cancel(u: Update, c):
    await u.message.reply_text("❌ Cancelled.", reply_markup=get_menu())
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("report", start_report), MessageHandler(filters.Regex("^Create Report$"), start_report)],
        states={USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)], AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)], EXPLANATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_explanation)], PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_proof_link)], CONFIRM: [CallbackQueryHandler(send_to_admin, pattern="^sub_adm$")]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    app.add_handler(CallbackQueryHandler(admin_buttons_handler, pattern="^(ok|no)_"))
    print("🚀 Bot running...")
    app.run_polling(close_loop=False, drop_pending_updates=True)

if __name__ == '__main__': 
    main()
