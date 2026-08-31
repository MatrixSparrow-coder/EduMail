"""
main.py - Main Telegram Bot
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import *
from database import Database
from generator import EduEmailGenerator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()
generator = EduEmailGenerator()

# ============ USER COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)

    user_data = db.get_user(user.id)
    status = user_data['status'] if user_data else 'pending'

    status_text = {'pending': '⏳ Pending', 'approved': '✅ Approved', 'rejected': '❌ Rejected'}.get(status, '❓ Unknown')

    keyboard = [
        [InlineKeyboardButton("📧 Generate Email", callback_data="generate")],
        [InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]

    message = WELCOME_MESSAGE.format(
        status=status_text,
        count=user_data.get('emails_generated', 0) if user_data else 0
    )

    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)

    if not user_data:
        await update.message.reply_text("❌ Use /start first.")
        return

    if user_data['status'] != 'approved':
        await update.message.reply_text("⏳ Your account is pending approval.")
        return

    balance = user_data['balance']
    price = float(db.get_setting('price_per_email') or 5)

    if balance < price:
        await update.message.reply_text(f"❌ Insufficient balance! Need ${price:.2f}, you have ${balance:.2f}")
        return

    await update.message.reply_text("🔄 Generating .edu email... Please wait 2-5 minutes.")

    result = generator.generate()

    if result['status'] == 'success':
        db.update_balance(user_id, -price)
        db.add_email(user_id, result['email'], result['password'], result['student_id'])

        message = f"""
🎓 **.EDU EMAIL GENERATED!**

📧 `{result['email']}`
🔑 `{result['password']}`
🆔 `{result['student_id']}`
👤 {result['full_name']}

🔗 Login: https://mylu.liberty.edu
💰 Balance Deducted: ${price:.2f}
💳 Remaining: ${(balance - price):.2f}

🔒 100% anonymous - No user data stored
"""
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Failed: {result.get('error', 'Unknown error')}")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    if not user_data:
        await update.message.reply_text("❌ Use /start first.")
        return

    emails = db.get_user_emails(user_id)
    email_list = "\n".join([f"  • `{e['email']}`" for e in emails[:3]])

    message = f"""
📊 **Your Status**
👤 ID: `{user_id}`
📌 Status: {user_data['status']}
💰 Balance: ${user_data['balance']:.2f}
📧 Emails: {user_data['emails_generated']}

📨 Recent:
{email_list if emails else 'No emails yet'}
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    if not user_data:
        await update.message.reply_text("❌ Use /start first.")
        return

    price = float(db.get_setting('price_per_email') or 5)
    await update.message.reply_text(f"""
💰 **Balance**
💵 Balance: ${user_data['balance']:.2f}
💲 Price/Email: ${price:.2f}
📧 Can generate: {int(user_data['balance'] // price)}

💳 Contact @{CONTACT['owner']} to add balance
""")

# ============ ADMIN COMMANDS ============

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /approve <user_id>")
        return

    target = int(context.args[0])
    if db.update_user_status(target, 'approved'):
        await update.message.reply_text(f"✅ User {target} approved.")
    else:
        await update.message.reply_text("❌ Failed.")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /reject <user_id>")
        return

    target = int(context.args[0])
    if db.update_user_status(target, 'rejected'):
        await update.message.reply_text(f"✅ User {target} rejected.")
    else:
        await update.message.reply_text("❌ Failed.")

async def addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /addbalance <user_id> <amount>")
        return

    target = int(context.args[0])
    amount = float(context.args[1])
    if db.update_balance(target, amount):
        await update.message.reply_text(f"✅ Added ${amount:.2f} to user {target}.")
    else:
        await update.message.reply_text("❌ Failed.")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return

    stats = db.get_statistics()
    await update.message.reply_text(f"""
📊 **Bot Stats**
👥 Total Users: {stats['total_users']}
✅ Approved: {stats['approved_users']}
⏳ Pending: {stats['pending_users']}
📧 Emails Generated: {stats['total_emails']}
💲 Price/Email: ${stats['price_per_email']:.2f}
""")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = db.get_all_users(status='approved')
    sent = 0
    for user in users:
        try:
            await context.bot.send_message(user['user_id'], f"📢 {message}")
            sent += 1
            await asyncio.sleep(0.5)
        except:
            pass
    await update.message.reply_text(f"✅ Sent to {sent} users.")

# ============ CALLBACKS ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "generate":
        await generate(update, context)
    elif query.data == "status":
        await status_cmd(update, context)
    elif query.data == "balance":
        await balance_cmd(update, context)
    elif query.data == "help":
        # ✅ FIX: 'update.message' ki jagah 'query.message' use kiya hai
        await query.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')

# ============ MAIN ============

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')))

    # Admin commands
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("addbalance", addbalance))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Callback
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot is running...")

    # ==========================================
    # 🚀 RENDER PORT 8080 FIX (YE NAYA CODE HAI)
    # ==========================================
    import threading
    import os
    from flask import Flask

    flask_app = Flask(__name__)

    @flask_app.route('/')
    def home():
        return "Bot is running!"

    def run_flask():
        # Render ka PORT variable use karo, agar nahi hai toh 8080
        port = int(os.environ.get('PORT', 8080))
        flask_app.run(host='0.0.0.0', port=port)

    # Flask ko background thread mein chalao
    t = threading.Thread(target=run_flask)
    t.start()
    # ==========================================
    # 🚀 RENDER PORT 8080 FIX END
    # ==========================================

    # ⚡ 100% Fix: Purane instance ka data clear karke naya start hoga
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()