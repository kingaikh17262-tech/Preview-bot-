import logging
import sqlite3
import random
import string
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = "8930896178:AAFzC7axCJHjWTLQQP-sqprKAK-o2NmTalk"
ADMIN_ID = 6888925459
CHANNELS = [
    {"name": "Main Channel", "id": "@aghubof", "url": "https://t.me/aghubof"},
    {"name": "Backup 1", "id": -1004338638206, "url": "https://t.me/+5dyAgek7OiRiNDRl"},
    {"name": "Backup 2", "id": -1004485538795, "url": "https://t.me/+G3H9ccmzqRtkZmI1"},
    {"name": "Backup 3 (18+)", "id": -1004302304402, "url": "https://t.me/+G3H9ccmzqRtkZmI1"}
]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
conn = sqlite3.connect("preview.db", check_same_thread=False)
cursor = conn.cursor()
# Naya Database schema (Size aur Type ke saath)
cursor.execute("""CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, media_ids TEXT, text TEXT, size_mb REAL)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT)""")
conn.commit()

admin_states = {}
admin_temp_data = {}

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        for ch in CHANNELS:
            member = await context.bot.get_chat_member(chat_id=ch["id"], user_id=update.effective_user.id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        return True
    except Exception: return False

async def send_join_msg(update: Update):
    text = "🚨 **Access Denied!**\n\nPlease join all our channels below to access the premium content.\n\n👇 **Click the buttons below to join:**"
    keyboard = []
    for ch in CHANNELS:
        keyboard.append([InlineKeyboardButton(f"📢 {ch['name']}", url=ch['url'], style="success")])
    keyboard.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_again", style="primary")])
    
    if update.callback_query: 
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else: 
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user.id, user.first_name))
    conn.commit()

    if not await check_join(update, context): return await send_join_msg(update)
        
    if context.args:
        post_id = context.args[0]
        cursor.execute("SELECT media_ids, text FROM posts WHERE id = ?", (post_id,))
        result = cursor.fetchone()
        
        if result:
            media_ids, caption_text = result
            
            # --- PREMIUM LOADING SCREEN ---
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
            msg = await update.message.reply_text("⚡ **Starting Secure Server...**\n[□□□□□□□□□□] 0%")
            await asyncio.sleep(0.3)
            await msg.edit_text("🛡️ **Bypassing Firewall...**\n[■■■■□□□□□□] 40%")
            await asyncio.sleep(0.3)
            await msg.edit_text("💎 **Decrypting Premium Photos...**\n[■■■■■■■■□□] 80%")
            await asyncio.sleep(0.3)
            await msg.edit_text("✅ **100% Complete! Sending Files...**")
            await asyncio.sleep(0.3)
            
            try:
                media_group = [InputMediaPhoto(media=mid) for mid in media_ids.split(",")]
                await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
                if caption_text and caption_text != "None":
                    await update.message.reply_text(caption_text, parse_mode='Markdown')
                await msg.delete() # Delete loading screen
            except Exception:
                await msg.edit_text("❌ Error sending photos. Please contact admin.")
            return
        else: return await update.message.reply_text("❌ Link expired or invalid.")

    welcome = f"👋 **Welcome {user.first_name}!**\n\nI am the **ANAS PREMIUM BOT**.\nYou opened this via a channel link. Your photos will be sent shortly.\n\n💠 **Premium Content** | ⚡ **Fast** | 🛡 **Safe**"
    keyboard = [[InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel", style="primary")]] if user.id == ADMIN_ID else []
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "check_again":
        if await check_join(update, context):
            await query.message.delete()
            await start(update, context)
        else: await query.answer("❌ You haven't joined all channels yet!", show_alert=True)
            
    elif data == "admin_panel":
        if update.effective_user.id != ADMIN_ID: return
        keyboard = [
            [InlineKeyboardButton("📤 Create Photo Post", callback_data="create_post", style="success")],
            [InlineKeyboardButton("📊 Detailed Stats", callback_data="bot_stats", style="primary")],
            [InlineKeyboardButton("🗑 Delete Post", callback_data="manage_posts", style="danger")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast", style="primary")]
        ]
        await query.edit_message_text("👑 **Admin Panel**\n\nWhat would you like to do?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    elif data == "create_post":
        admin_states[update.effective_user.id] = "awaiting_count"
        await query.edit_message_text("📤 **Photo Post Creation**\n\nHow many photos do you want to add? (Send a number, e.g., `2`)")
        
    elif data == "bot_stats":
        cursor.execute("SELECT COUNT(*) FROM users"); users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*), SUM(size_mb) FROM posts"); posts_data = cursor.fetchone()
        total_posts = posts_data[0] or 0
        total_size = posts_data[1] or 0.0
        
        size_text = f"{total_size:.2f} MB" if total_size < 1024 else f"{(total_size/1024):.2f} GB"
        
        stats_text = (
            f"📊 **Live Bot Statistics**\n\n"
            f"👥 **Total Users:** `{users}`\n"
            f"🖼️ **Total Photos Uploaded:** `{total_posts}`\n"
            f"💾 **Total Storage Used (Telegram Cloud):** `{size_text}`\n\n"
            f"🚀 **Server Status:** ONLINE"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="danger")]]
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "manage_posts":
        cursor.execute("SELECT id, text, size_mb FROM posts")
        all_posts = cursor.fetchall()
        if not all_posts:
            return await query.answer("No posts available to delete.", show_alert=True)
            
        keyboard = []
        for pid, ptext, psize in all_posts:
            btn_text = f"❌ {ptext[:15]}... ({psize:.1f}MB)" if ptext and ptext != "None" else f"❌ Post ID: {pid} ({psize:.1f}MB)"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"del_{pid}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="primary")])
        
        await query.edit_message_text("🗑 **Select a post to delete:**\n_Note: Deleting from here will stop the bot from sending it, but won't delete from Telegram's servers._", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data.startswith("del_"):
        post_id = data.split("_")[1]
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        await query.answer("✅ Post Deleted Successfully from Bot!", show_alert=True)
        # Refresh list
        await query.message.delete()
        await button_handler(update, context) # trigger manage_posts again

    elif data == "broadcast":
        admin_states[update.effective_user.id] = "awaiting_broadcast"
        await query.edit_message_text("📢 **Broadcast Mode**\n\nSend the message you want to broadcast to all users.")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    state = admin_states.get(user_id)
    
    if state == "awaiting_count":
        try:
            count = int(update.message.text)
            admin_temp_data[user_id] = {"count": count, "media": [], "size": 0.0, "current_index": 0}
            admin_states[user_id] = "awaiting_media"
            await update.message.reply_text(f"✅ Okay, we need {count} photos.\n\n📥 **Send the first photo:**")
        except ValueError: await update.message.reply_text("❌ Please send a valid number.")
            
    elif state == "awaiting_media":
        if update.message.photo:
            data = admin_temp_data[user_id]
            photo = update.message.photo[-1]
            data["media"].append(photo.file_id)
            data["size"] += (photo.file_size / (1024 * 1024)) # Convert to MB
            data["current_index"] += 1
            
            if data["current_index"] < data["count"]:
                await update.message.reply_text(f"✅ Photo {data['current_index']} saved!\n\n📥 **Send the next photo:**")
            else:
                admin_states[user_id] = "awaiting_text"
                await update.message.reply_text("✅ All photos saved!\n\n✍️ **Now send the Caption/Text** (or type `/skip` to skip).")
        else: await update.message.reply_text("❌ Invalid format. Please send a photo.")
            
    elif state == "awaiting_text":
        data = admin_temp_data[user_id]
        text = update.message.text
        if text.lower() == "/skip": text = "None"
        
        post_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        cursor.execute("INSERT INTO posts (id, media_ids, text, size_mb) VALUES (?, ?, ?, ?)", (post_id, ",".join(data["media"]), text, data["size"]))
        conn.commit()
        
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={post_id}"
        await update.message.reply_text(f"🎉 **Post Created Successfully!**\n\n🔗 **Your Link:**\n`{link}`\n\n_Use this link in your channel._", parse_mode='Markdown')
        admin_states[user_id] = None; admin_temp_data[user_id] = None

    elif state == "awaiting_broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        status_msg = await update.message.reply_text("⏳ Broadcasting...")
        success = 0
        for u in users:
            try:
                await update.message.copy(chat_id=u[0])
                success += 1
            except: pass
        await status_msg.edit_text(f"✅ **Broadcast Sent to {success} users!**")
        admin_states[user_id] = None

if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_messages))
    print("🚀 PREVIEW BOT STARTED!")
    # drop_pending_updates ensures instant fast startup
    app.run_polling(drop_pending_updates=True)