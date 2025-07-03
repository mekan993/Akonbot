import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Logging sazlamak
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot maglumatary
BOT_TOKEN = "7271748139:AAGS9Y0gARqDa-KGniq9hyQFNhpP4xoVK80"
ADMIN_ID = 7394635812

# Maglumatlar üçin faýl adlary
DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"
CHANNELS_FILE = f"{DATA_DIR}/channels.json"
LINKS_FILE = f"{DATA_DIR}/links.json"
CONFIG_FILE = f"{DATA_DIR}/config.json"

# Maglumatlary saklamak üçin papka döretmek
os.makedirs(DATA_DIR, exist_ok=True)

# Global maglumatlar
class BotData:
    def __init__(self):
        self.users = self.load_data(USERS_FILE, {})
        self.admins = self.load_data(ADMINS_FILE, [ADMIN_ID])
        self.channels = self.load_data(CHANNELS_FILE, [])
        self.links = self.load_data(LINKS_FILE, [])
        self.config = self.load_data(CONFIG_FILE, {"sponsor_code": "SPONSOR-123"})
    
    def load_data(self, filename, default):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    
    def save_users(self):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def save_admins(self):
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.admins, f, ensure_ascii=False, indent=2)
    
    def save_channels(self):
        with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.channels, f, ensure_ascii=False, indent=2)
    
    def save_links(self):
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.links, f, ensure_ascii=False, indent=2)
    
    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

bot_data = BotData()

# Admin barlamak
def is_admin(user_id):
    return user_id in bot_data.admins

# Kanal agzalygyny barlamak
async def check_channel_membership(context, user_id):
    if not bot_data.channels:
        return True
    
    for channel in bot_data.channels:
        try:
            member = await context.bot.get_chat_member(channel['channel_id'], user_id)
            if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                return False
        except:
            continue
    return True

# /start buýrugy
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Ulanyjy maglumatlaryny saklamak
    if str(user_id) not in bot_data.users:
        bot_data.users[str(user_id)] = {
            "id": user_id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "join_date": datetime.now().isoformat(),
            "code_received": False
        }
        bot_data.save_users()
    
    # Admin paneli görkezmek
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("📄 Kod Üýtget", callback_data="change_code")],
            [InlineKeyboardButton("📢 Kanal Goş", callback_data="add_channel"),
             InlineKeyboardButton("🗑️ Kanal Poz", callback_data="remove_channel")],
            [InlineKeyboardButton("🔗 Link Goş", callback_data="add_link"),
             InlineKeyboardButton("🗑️ Link Poz", callback_data="remove_link")],
            [InlineKeyboardButton("📤 Habar Iber", callback_data="send_message")],
            [InlineKeyboardButton("👤 Admin Goş", callback_data="add_admin"),
             InlineKeyboardButton("🗑️ Admin Poz", callback_data="remove_admin")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
             InlineKeyboardButton("🗃️ Ulanyjy Sanawy", callback_data="user_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔐 *Admin Panel*\n\n"
            f"Hoş geldiňiz! Botdan dolandyrmak üçin aşakdaky düwmeleri ulanyň.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    # Adi ulanyjy üçin kanal barlamak
    if not bot_data.channels:
        # Kanal ýok bolsa, göni kod bermek
        code = bot_data.config["sponsor_code"]
        bot_data.users[str(user_id)]["code_received"] = True
        bot_data.save_users()
        
        await update.message.reply_text(
            f"🎉 *Hoş geldiňiz!*\n\n"
            f"Siziň sponsor kodyňyz: `{code}`\n\n"
            f"Bu kody kopýa ediň we ulanmagazyň!",
            parse_mode='Markdown'
        )
        return
    
    # Kanal agzalygyny barlamak
    is_member = await check_channel_membership(context, user_id)
    
    if not is_member:
        # Kanallary görkezmek
        keyboard = []
        for channel in bot_data.channels:
            keyboard.append([InlineKeyboardButton(
                channel['button_text'], 
                url=f"https://t.me/{channel['channel_id'].replace('@', '')}"
            )])
        
        # Goşmaça linkler goşmak
        for link in bot_data.links:
            keyboard.append([InlineKeyboardButton(link['button_text'], url=link['url'])])
        
        keyboard.append([InlineKeyboardButton("✅ Agza boldym", callback_data="check_membership")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔔 *Sponsor Botiňa Hoş Geldiňiz!*\n\n"
            "Sponsor kody almak üçin ilki bilen aşakdaky kanallara agza boluň:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        # Kod bermek
        code = bot_data.config["sponsor_code"]
        bot_data.users[str(user_id)]["code_received"] = True
        bot_data.save_users()
        
        await update.message.reply_text(
            f"🎉 *Siziň sponsor kodyňyz taýýar!*\n\n"
            f"Kod: `{code}`\n\n"
            f"Bu kody kopýa ediň we ulanmagazyň!",
            parse_mode='Markdown'
        )

# Callback hadleri
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if not is_admin(user_id) and data != "check_membership":
        await query.edit_message_text("❌ Siziň bu funksiýa ulanmaga hukugyňyz ýok!")
        return
    
    # Agzalygy barlamak
    if data == "check_membership":
        is_member = await check_channel_membership(context, user_id)
        
        if is_member:
            code = bot_data.config["sponsor_code"]
            bot_data.users[str(user_id)]["code_received"] = True
            bot_data.save_users()
            
            await query.edit_message_text(
                f"🎉 *Siziň sponsor kodyňyz taýýar!*\n\n"
                f"Kod: `{code}`\n\n"
                f"Bu kody kopýa ediň we ulanmagazyň!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ Siz henizem ähli kanallara agza bolmadyňyz!\n\n"
                "Iltimos, ähli kanallara agza boluň we täzeden synanyň."
            )
        return
    
    # Admin funksiýalary
    if data == "change_code":
        await query.edit_message_text(
            "📝 *Kod Üýtgetmek*\n\n"
            f"Häzirki kod: `{bot_data.config['sponsor_code']}`\n\n"
            "Täze kody ýazyň:"
        )
        context.user_data['awaiting'] = 'new_code'
    
    elif data == "add_channel":
        await query.edit_message_text(
            "📢 *Kanal Goşmak*\n\n"
            "Kanal ID-ni @username görnüşinde ýazyň:\n"
            "Mysal: @mykanaly"
        )
        context.user_data['awaiting'] = 'channel_id'
    
    elif data == "remove_channel":
        if not bot_data.channels:
            await query.edit_message_text("❌ Hiç hili kanal goşulmadyk!")
            return
        
        keyboard = []
        for i, channel in enumerate(bot_data.channels):
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {channel['name']}", 
                callback_data=f"del_channel_{i}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Yzyna", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🗑️ *Kanal Pozmak*\n\nPozmak üçin kanaly saýlaň:",
            reply_markup=reply_markup
        )
    
    elif data.startswith("del_channel_"):
        index = int(data.split("_")[2])
        if 0 <= index < len(bot_data.channels):
            removed = bot_data.channels.pop(index)
            bot_data.save_channels()
            await query.edit_message_text(f"✅ '{removed['name']}' kanaly pozuldy!")
    
    elif data == "add_link":
        await query.edit_message_text(
            "🔗 *Link Goşmak*\n\n"
            "Link URL-ni ýazyň:\n"
            "Mysal: https://t.me/mykanaly ýa-da https://example.com"
        )
        context.user_data['awaiting'] = 'link_url'
    
    elif data == "remove_link":
        if not bot_data.links:
            await query.edit_message_text("❌ Hiç hili link goşulmadyk!")
            return
        
        keyboard = []
        for i, link in enumerate(bot_data.links):
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {link['button_text']}", 
                callback_data=f"del_link_{i}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Yzyna", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🗑️ *Link Pozmak*\n\nPozmak üçin linki saýlaň:",
            reply_markup=reply_markup
        )
    
    elif data.startswith("del_link_"):
        index = int(data.split("_")[2])
        if 0 <= index < len(bot_data.links):
            removed = bot_data.links.pop(index)
            bot_data.save_links()
            await query.edit_message_text(f"✅ '{removed['button_text']}' linki pozuldy!")
    
    elif data == "send_message":
        await query.edit_message_text(
            "📤 *Ähli Ulanyjylara Habar*\n\n"
            "Ibermek isleýän habaryňyzy ýazyň:"
        )
        context.user_data['awaiting'] = 'broadcast_message'
    
    elif data == "add_admin":
        await query.edit_message_text(
            "👤 *Admin Goşmak*\n\n"
            "Täze adminiň ID-ni ýazyň:"
        )
        context.user_data['awaiting'] = 'new_admin'
    
    elif data == "remove_admin":
        admin_list = [admin for admin in bot_data.admins if admin != ADMIN_ID]
        if not admin_list:
            await query.edit_message_text("❌ Pozmak üçin admin ýok!")
            return
        
        keyboard = []
        for admin in admin_list:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {admin}", 
                callback_data=f"del_admin_{admin}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Yzyna", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🗑️ *Admin Pozmak*\n\nPozmak üçin admini saýlaň:",
            reply_markup=reply_markup
        )
    
    elif data.startswith("del_admin_"):
        admin_id = int(data.split("_")[2])
        if admin_id in bot_data.admins and admin_id != ADMIN_ID:
            bot_data.admins.remove(admin_id)
            bot_data.save_admins()
            await query.edit_message_text(f"✅ Admin {admin_id} pozuldy!")
    
    elif data == "stats":
        total_users = len(bot_data.users)
        code_received = len([u for u in bot_data.users.values() if u.get('code_received', False)])
        total_admins = len(bot_data.admins)
        total_channels = len(bot_data.channels)
        
        stats_text = (
            f"📊 *Bot Statistikasy*\n\n"
            f"👥 Jemi ulanyjylar: {total_users}\n"
            f"✅ Kod alanlar: {code_received}\n"
            f"👤 Adminler: {total_admins}\n"
            f"📢 Kanallar: {total_channels}\n"
            f"🔗 Linkler: {len(bot_data.links)}\n"
            f"📝 Häzirki kod: `{bot_data.config['sponsor_code']}`"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Yzyna", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif data == "user_list":
        if not bot_data.users:
            await query.edit_message_text("❌ Hiç hili ulanyjy ýok!")
            return
        
        user_text = "🗃️ *Ulanyjy Sanawy*\n\n"
        for user_data in list(bot_data.users.values())[:10]:  # Ilkinji 10 ulanyjy
            user_text += (
                f"ID: {user_data['id']}\n"
                f"Ady: {user_data.get('first_name', 'Näbelli')}\n"
                f"Kod aldy: {'✅' if user_data.get('code_received', False) else '❌'}\n"
                f"Goşulan: {user_data['join_date'][:10]}\n\n"
            )
        
        if len(bot_data.users) > 10:
            user_text += f"... we ýene {len(bot_data.users) - 10} ulanyjy"
        
        keyboard = [[InlineKeyboardButton("🔙 Yzyna", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(user_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("📄 Kod Üýtget", callback_data="change_code")],
            [InlineKeyboardButton("📢 Kanal Goş", callback_data="add_channel"),
             InlineKeyboardButton("🗑️ Kanal Poz", callback_data="remove_channel")],
            [InlineKeyboardButton("🔗 Link Goş", callback_data="add_link"),
             InlineKeyboardButton("🗑️ Link Poz", callback_data="remove_link")],
            [InlineKeyboardButton("📤 Habar Iber", callback_data="send_message")],
            [InlineKeyboardButton("👤 Admin Goş", callback_data="add_admin"),
             InlineKeyboardButton("🗑️ Admin Poz", callback_data="remove_admin")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
             InlineKeyboardButton("🗃️ Ulanyjy Sanawy", callback_data="user_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔐 *Admin Panel*\n\n"
            "Hoş geldiňiz! Botdan dolandyrmak üçin aşakdaky düwmeleri ulanyň.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

# Habar garaşmak
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not is_admin(user_id):
        return
    
    awaiting = context.user_data.get('awaiting')
    
    if awaiting == 'new_code':
        bot_data.config['sponsor_code'] = text
        bot_data.save_config()
        await update.message.reply_text(f"✅ Kod üýtgedildi: `{text}`", parse_mode='Markdown')
        context.user_data['awaiting'] = None
    
    elif awaiting == 'channel_id':
        context.user_data['new_channel'] = {'channel_id': text}
        await update.message.reply_text(
            f"📢 Kanal ID: {text}\n\n"
            "Indi kanal adyny ýazyň:"
        )
        context.user_data['awaiting'] = 'channel_name'
    
    elif awaiting == 'channel_name':
        context.user_data['new_channel']['name'] = text
        await update.message.reply_text(
            f"📢 Kanal ady: {text}\n\n"
            "Indi düwmäniň adyny ýazyň:"
        )
        context.user_data['awaiting'] = 'channel_button'
    
    elif awaiting == 'channel_button':
        context.user_data['new_channel']['button_text'] = text
        bot_data.channels.append(context.user_data['new_channel'])
        bot_data.save_channels()
        
        await update.message.reply_text("✅ Kanal üstünlikli goşuldy!")
        context.user_data['awaiting'] = None
        context.user_data['new_channel'] = None
    
    elif awaiting == 'link_url':
        context.user_data['new_link'] = {'url': text}
        await update.message.reply_text(
            f"🔗 Link: {text}\n\n"
            "Indi düwmäniň adyny ýazyň:"
        )
        context.user_data['awaiting'] = 'link_button'
    
    elif awaiting == 'link_button':
        context.user_data['new_link']['button_text'] = text
        bot_data.links.append(context.user_data['new_link'])
        bot_data.save_links()
        
        await update.message.reply_text("✅ Link üstünlikli goşuldy!")
        context.user_data['awaiting'] = None
        context.user_data['new_link'] = None
    
    elif awaiting == 'broadcast_message':
        sent_count = 0
        failed_count = 0
        
        for user_id_str in bot_data.users:
            try:
                await context.bot.send_message(int(user_id_str), text)
                sent_count += 1
            except:
                failed_count += 1
        
        await update.message.reply_text(
            f"📤 *Habar Ugradyldy*\n\n"
            f"✅ Üstünlikli: {sent_count}\n"
            f"❌ Şowsuz: {failed_count}",
            parse_mode='Markdown'
        )
        context.user_data['awaiting'] = None
    
    elif awaiting == 'new_admin':
        try:
            new_admin_id = int(text)
            if new_admin_id not in bot_data.admins:
                bot_data.admins.append(new_admin_id)
                bot_data.save_admins()
                await update.message.reply_text(f"✅ Admin {new_admin_id} goşuldy!")
            else:
                await update.message.reply_text("❌ Bu ulanyjy eýýäm admin!")
        except:
            await update.message.reply_text("❌ Nädogry ID! Diňe sanlar ýazyň.")
        
        context.user_data['awaiting'] = None

# Esasy funksiýa
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handler-lary goşmak
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Boti işletmek
    print("🤖 Telegram Sponsor Bot başlady...")
    application.run_polling()

if __name__ == '__main__':
    main()
    
