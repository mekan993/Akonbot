import os
import sys
import subprocess
import time
import random
import threading
from datetime import datetime
import json

# Gerekli paketleri awtomatiki gurmak
def install_required_packages():
    """Gerekli Python paketlerini gurmak"""
    required_packages = [
        'pyTelegramBotAPI',
        'requests',
        'flask'
    ]
    
    print("📦 Python paketleri barlanýar...")
    
    for package in required_packages:
        try:
            __import__(package.replace('pyTelegramBotAPI', 'telebot'))
        except ImportError:
            print(f"📥 {package} gurulýar...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ {package} üstünlikli guruldy")
            except subprocess.CalledProcessError:
                print(f"❌ {package} gurmak şowsuz boldy")
                return False
    
    print("✅ Ähli paketler taýýar!")
    return True

# Paketleri gur
if not install_required_packages():
    print("❌ Paketleri gurmak başa barmady!")
    sys.exit(1)

# Indi import edip bileris
import telebot
from telebot import types
import requests
from flask import Flask, jsonify
import threading

# Bot konfiguarasiýasy
BOT_TOKEN = '8184917004:AAEMQ6BlUFo-ja_Ms15adOfixRjj7zbBtX0'
BOT_OWNER_ID = 7394635812
PORT = 3000

# Bot döretmek
bot = telebot.TeleBot(BOT_TOKEN)

# Flask server döretmek
app = Flask(__name__)

# Global üýtgeýjiler
active_games = {}  # Chat ID -> {secret_number, max, participants: set(), started_by, flag}
admin_list = {BOT_OWNER_ID}
banned_words = set()
chat_list = set()
statistics = {
    'total_mutes': 0,
    'total_bans': 0,
    'total_warns': 0,
    'total_games': 0
}

start_message = """🤖 Salam! Men AKON MODER BOT!

🎮 San tapmaca oýny üçin: /Random_77
🛡️ Moderasiýa komandalary:
• /mute 
• /warn 
• /ban 
Üns Beriň: Berilen Buýruk yzyna Alynmaýar

📞 Kömek üçin: @Tdm1912"""

waiting_for_input = {}  # user_id -> {type: 'broadcast'|'add_admin'|'edit_start'|'user_search', chat_id}

print("🤖 AKON MODER BOT başlady!")
print(f"👤 Bot eýesi: {BOT_OWNER_ID}")
print(f"🔑 Token: {BOT_TOKEN[:20]}...")

# Admin ýoklamak funksiýasy
def is_admin(chat_id, user_id):
    """Ulanyjynyň admin bardygyny barlamak"""
    # Bot eýesi hemişe admin
    if user_id == BOT_OWNER_ID:
        return True
    
    # Admin sanawynda barlamak
    if user_id in admin_list:
        return True
    
    # Çat adminlerini barlamak
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['administrator', 'creator']
    except:
        return False

# Başlamak komandasy
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Çaty sanawa goşmak
    chat_list.add(chat_id)
    
    # Knopkalar döretmek
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🎮 Oýun başlat", callback_data="start_game"))
    keyboard.add(types.InlineKeyboardButton("📊 Statistika", callback_data="statistics"))
    
    # Eger bot eýesi bolsa admin panel goşmak
    if user_id == BOT_OWNER_ID and message.chat.type == 'private':
        keyboard.add(types.InlineKeyboardButton("🔒 Admin Panel", callback_data="admin_panel"))
    
    bot.send_message(chat_id, start_message, reply_markup=keyboard)

# San tapmaca oýny
@bot.message_handler(regexp=r'/Random_(\d+)(?:\s+(.+))?')
def random_game(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Regex bilen maksimum sany we baýragy almak
    import re
    match = re.match(r'/Random_(\d+)(?:\s+(.+))?', message.text)
    max_number = int(match.group(1))
    flag = match.group(2) if match.group(2) else None
    
    if max_number < 1:
        bot.send_message(chat_id, '❌ San 1-den uly bolmaly!')
        return
    
    if max_number > 1000000:
        bot.send_message(chat_id, '❌ San 1,000,000-dan kiçi bolmaly!')
        return
    
    # Gizlin sany döretmek
    secret_number = random.randint(1, max_number)
    
    # Oýuny başlatmak
    active_games[chat_id] = {
        'secret_number': secret_number,
        'max': max_number,
        'participants': set(),
        'started_by': username,
        'flag': flag,
        'start_time': datetime.now()
    }
    
    # Bot eýesine gizlin sany ibermek
    try:
        owner_message = f"""🎯 Täze oýun başlady!

💬 Çat: {message.chat.title or 'Şahsy çat'}
🆔 Chat ID: {chat_id}
🎲 Gizlin san: {secret_number}
📊 Aralyk: 1-{max_number}
👤 Başlatan: @{username}"""
        
        if flag:
            owner_message += f"\n🏴 Bayrak: {flag}"
        
        bot.send_message(BOT_OWNER_ID, owner_message)
    except:
        print('Bot eýesine SMS iberip bolmady')
    
    # Çata oýun başlama habary
    game_message = f"""🎮 San tapmaca oýny başlady!

🎯 1-den {max_number} çenli san tapmaly!
👤 Başlatan: @{username}"""
    
    if flag:
        game_message += f"\n🏴 {flag}"
    
    game_message += "\n\n💡 Sany ýazyň we tapmaga synanyşyň!"
    
    bot.send_message(chat_id, game_message)
    statistics['total_games'] += 1

# Mute komandasy
@bot.message_handler(regexp=r'/mute(?:\s+(\d+))?(?:\s+(.+))?')
def mute_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Admin ýoklamasy
    if not is_admin(chat_id, user_id):
        bot.send_message(chat_id, '❌ Size bu komandany ulanmaga rugsat ýok!')
        return
    
    # Reply barlamasy
    if not message.reply_to_message:
        bot.send_message(chat_id, '❌ Kimdir birine jogap beriň!')
        return
    
    target_user = message.reply_to_message.from_user
    
    # Regex bilen sagat we sebäbi almak
    import re
    match = re.match(r'/mute(?:\s+(\d+))?(?:\s+(.+))?', message.text)
    hours = int(match.group(1)) if match.group(1) else 1
    reason = match.group(2) if match.group(2) else 'Sebäp görkezilmedi'
    
    try:
        # Ulanyjyny mute etmek
        mute_until = int(time.time()) + (hours * 3600)
        bot.restrict_chat_member(
            chat_id, 
            target_user.id,
            until_date=mute_until,
            can_send_messages=False
        )
        
        response = f"""👤 Ulanyjy: @{target_user.username or target_user.first_name}
👮 Admin: @{username}
🚫 Çäre: Mute
⏱ Wagt: {hours} sagat
🎯 Sebäp: {reason}"""
        
        # Eger bot eýesi admin däl bolsa goşmaça habar
        if user_id == BOT_OWNER_ID and not is_admin(chat_id, user_id):
            response += "\n\n⚠️ Bu buýruk botyň eýesinden geldi.\n🔥 Buýruk uly ýerden!"
        
        bot.send_message(chat_id, response)
        statistics['total_mutes'] += 1
        
    except Exception as e:
        bot.send_message(chat_id, f'❌ Mute edip bolmady: {str(e)}')

# Warn komandasy
@bot.message_handler(regexp=r'/warn(?:\s+(\d+))?(?:\s+(.+))?')
def warn_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    if not is_admin(chat_id, user_id):
        bot.send_message(chat_id, '❌ Size bu komandany ulanmaga rugsat ýok!')
        return
    
    if not message.reply_to_message:
        bot.send_message(chat_id, '❌ Kimdir birine jogap beriň!')
        return
    
    target_user = message.reply_to_message.from_user
    
    # Regex bilen warn sany we sebäbi almak
    import re
    match = re.match(r'/warn(?:\s+(\d+))?(?:\s+(.+))?', message.text)
    warn_count = int(match.group(1)) if match.group(1) else 1
    reason = match.group(2) if match.group(2) else 'Sebäp görkezilmedi'
    
    response = f"""👤 Ulanyjy: @{target_user.username or target_user.first_name}
👮 Admin: @{username}
🚫 Çäre: Warn
⚠️ Sany: {warn_count}
🎯 Sebäp: {reason}"""
    
    if user_id == BOT_OWNER_ID and not is_admin(chat_id, user_id):
        response += "\n\n⚠️ Bu buýruk botyň eýesinden geldi.\n🔥 Buýruk uly ýerden!"
    
    bot.send_message(chat_id, response)
    statistics['total_warns'] += warn_count

# Ban komandasy
@bot.message_handler(regexp=r'/ban(?:\s+(.+))?')
def ban_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    if not is_admin(chat_id, user_id):
        bot.send_message(chat_id, '❌ Size bu komandany ulanmaga rugsat ýok!')
        return
    
    if not message.reply_to_message:
        bot.send_message(chat_id, '❌ Kimdir birine jogap beriň!')
        return
    
    target_user = message.reply_to_message.from_user
    
    # Regex bilen sebäbi almak
    import re
    match = re.match(r'/ban(?:\s+(.+))?', message.text)
    reason = match.group(1) if match.group(1) else 'Sebäp görkezilmedi'
    
    try:
        bot.ban_chat_member(chat_id, target_user.id)
        
        response = f"""👤 Ulanyjy: @{target_user.username or target_user.first_name}
👮 Admin: @{username}
🚫 Çäre: Ban
🎯 Sebäp: {reason}"""
        
        if user_id == BOT_OWNER_ID and not is_admin(chat_id, user_id):
            response += "\n\n⚠️ Bu buýruk botyň eýesinden geldi.\n🔥 Buýruk uly ýerden!"
        
        bot.send_message(chat_id, response)
        statistics['total_bans'] += 1
        
    except Exception as e:
        bot.send_message(chat_id, f'❌ Ban edip bolmady: {str(e)}')

# Gadagan söz goşmak
@bot.message_handler(regexp=r'/addban (.+)')
def add_banned_word(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if user_id != BOT_OWNER_ID:
        bot.send_message(chat_id, '❌ Size rugsat ýok!')
        return
    
    import re
    match = re.match(r'/addban (.+)', message.text)
    word = match.group(1).lower().strip()
    banned_words.add(word)
    
    bot.send_message(chat_id, f'✅ "{word}" gadagan sözler sanawyna goşuldy!')

# Gadagan söz aýyrmak
@bot.message_handler(regexp=r'/removeban (.+)')
def remove_banned_word(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if user_id != BOT_OWNER_ID:
        bot.send_message(chat_id, '❌ Size rugsat ýok!')
        return
    
    import re
    match = re.match(r'/removeban (.+)', message.text)
    word = match.group(1).lower().strip()
    
    if word in banned_words:
        banned_words.remove(word)
        bot.send_message(chat_id, f'✅ "{word}" gadagan sözler sanawyndan aýyryldy!')
    else:
        bot.send_message(chat_id, f'❌ "{word}" gadagan sözler sanawynda ýok!')

# Callback query işlemek
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data
    
    bot.answer_callback_query(call.id)
    
    if data == 'start_game':
        bot.send_message(chat_id, """🎮 Oýun başlatmak üçin:
/Random_100 - 1-100 aralygynda
/Random_77 - 1-77 aralygynda

Mysal: /Random_77 1 Ýyldyz""")
        
    elif data == 'statistics':
        stats = f"""📊 Statistika:

🎮 Jemi oýunlar: {statistics['total_games']}
🔇 Jemi mute: {statistics['total_mutes']}
⚠️ Jemi warn: {statistics['total_warns']}
🚫 Jemi ban: {statistics['total_bans']}
🎯 Aktiw oýunlar: {len(active_games)}
💬 Jemi çatlar: {len(chat_list)}"""
        
        bot.send_message(chat_id, stats)
        
    elif data == 'admin_panel':
        if user_id != BOT_OWNER_ID:
            bot.send_message(chat_id, '❌ Size rugsat ýok!')
            return
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📢 Habar ibermek", callback_data="send_broadcast"))
        keyboard.add(types.InlineKeyboardButton("👤 Admin bermek", callback_data="add_admin"))
        keyboard.add(types.InlineKeyboardButton("🗑️ Gadagan söz", callback_data="banned_words"))
        keyboard.add(types.InlineKeyboardButton("🔎 Ulanyjy gözlemek", callback_data="user_search"))
        keyboard.add(types.InlineKeyboardButton("🧾 Aktiw oýunlar", callback_data="active_games"))
        keyboard.add(types.InlineKeyboardButton("⚙️ Ana menü üýtgetmek", callback_data="edit_start_message"))
        keyboard.add(types.InlineKeyboardButton("🔙 Yza", callback_data="back_to_main"))
        
        bot.send_message(chat_id, "🔒 Admin Panel\n\nSaýlaň:", reply_markup=keyboard)
        
    elif data == 'send_broadcast':
        if user_id != BOT_OWNER_ID:
            return
        waiting_for_input[user_id] = {'type': 'broadcast', 'chat_id': chat_id}
        bot.send_message(chat_id, '📢 Ähli çatlara iberilýän habary ýazyň:')
        
    elif data == 'add_admin':
        if user_id != BOT_OWNER_ID:
            return
        waiting_for_input[user_id] = {'type': 'add_admin', 'chat_id': chat_id}
        bot.send_message(chat_id, '👤 Admin etmek isleýän ulanyjynyň ID-sini ýazyň:')
        
    elif data == 'edit_start_message':
        if user_id != BOT_OWNER_ID:
            return
        waiting_for_input[user_id] = {'type': 'edit_start', 'chat_id': chat_id}
        bot.send_message(chat_id, f"""⚙️ Häzirki ana menü habary:

{start_message}

📝 Täze ana menü habaryny ýazyň:""")
        
    elif data == 'banned_words':
        if user_id != BOT_OWNER_ID:
            return
        
        banned_list = '🗑️ Gadagan sözler:\n\n'
        if not banned_words:
            banned_list += 'Heniz gadagan söz goşulmadyk'
        else:
            for i, word in enumerate(banned_words, 1):
                banned_list += f'{i}. {word}\n'
        
        banned_list += '\n💡 Gadagan söz goşmak üçin: /addban söz\n💡 Gadagan söz aýyrmak üçin: /removeban söz'
        bot.send_message(chat_id, banned_list)
        
    elif data == 'user_search':
        if user_id != BOT_OWNER_ID:
            return
        waiting_for_input[user_id] = {'type': 'user_search', 'chat_id': chat_id}
        bot.send_message(chat_id, '🔎 Gözlemek isleýän ulanyjynyň ID-sini ýa-da @username-ini ýazyň:')
        
    elif data == 'active_games':
        if user_id != BOT_OWNER_ID:
            return
        
        if not active_games:
            bot.send_message(chat_id, '📭 Aktiw oýun ýok')
            return
        
        games_list = '🧾 Aktiw oýunlar:\n\n'
        for i, (game_chat_id, game) in enumerate(active_games.items(), 1):
            games_list += f"{i}. Chat ID: {game_chat_id}\n"
            games_list += f"   🎯 Gizlin san: {game['secret_number']}\n"
            games_list += f"   📊 Aralyk: 1-{game['max']}\n"
            games_list += f"   👥 Gatnaşyjy: {len(game['participants'])}\n"
            games_list += f"   👤 Başlatan: {game['started_by']}\n"
            if game['flag']:
                games_list += f"   🏴 {game['flag']}\n"
            games_list += '\n'
        
        bot.send_message(chat_id, games_list)
        
    elif data == 'back_to_main':
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🎮 Oýun başlat", callback_data="start_game"))
        keyboard.add(types.InlineKeyboardButton("📊 Statistika", callback_data="statistics"))
        
        if user_id == BOT_OWNER_ID:
            keyboard.add(types.InlineKeyboardButton("🔒 Admin Panel", callback_data="admin_panel"))
        
        bot.send_message(chat_id, start_message, reply_markup=keyboard)

# Ähli habarlary işlemek
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    global start_message
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    message_text = message.text
    
    if not message_text:
        return
    
    # Çaty sanawa goşmak
    chat_list.add(chat_id)
    
    # Eger ulanyjydan garaşylýan jogap bar bolsa
    if user_id in waiting_for_input:
        input_data = waiting_for_input[user_id]
        
        if input_data['type'] == 'broadcast':
            # Ähli çatlara habar ibermek
            sent_count = 0
            error_count = 0
            
            bot.send_message(chat_id, '📤 Habar iberilýär...')
            
            for target_chat_id in chat_list:
                try:
                    bot.send_message(target_chat_id, f'📢 Duyduryş:\n\n{message_text}')
                    sent_count += 1
                    time.sleep(0.1)  # SMS arasynda arakesme
                except:
                    error_count += 1
            
            bot.send_message(chat_id, f'✅ Habar iberildi!\n📊 Üstünlikli: {sent_count}\n❌ Ýalňyşlyk: {error_count}')
            del waiting_for_input[user_id]
            
        elif input_data['type'] == 'add_admin':
            try:
                new_admin_id = int(message_text)
                admin_list.add(new_admin_id)
                bot.send_message(chat_id, f'✅ {new_admin_id} ID-li ulanyjy admin edildi!')
            except ValueError:
                bot.send_message(chat_id, '❌ Dogry ID ýazyň!')
            del waiting_for_input[user_id]
            
        elif input_data['type'] == 'edit_start':
            start_message = message_text
            bot.send_message(chat_id, '✅ Ana menü habary üýtgedildi!')
            del waiting_for_input[user_id]
            
        elif input_data['type'] == 'user_search':
            search_result = f"""🔎 Gözleg: {message_text}

📊 Häzirki statistika:
💬 Jemi çatlar: {len(chat_list)}
🎮 Aktiw oýunlar: {len(active_games)}
👮 Adminler: {len(admin_list)}
🗑️ Gadagan sözler: {len(banned_words)}"""
            
            bot.send_message(chat_id, search_result)
            del waiting_for_input[user_id]
            
        return
    
    # San tapmaca oýny üçin san barlamak
    if chat_id in active_games and message_text.isdigit():
        game = active_games[chat_id]
        guessed_number = int(message_text)
        
        # Gatnaşyjyny goşmak
        game['participants'].add(user_id)
        
        # Dogrulygy barlamak
        if guessed_number == game['secret_number']:
            username = message.from_user.username or message.from_user.first_name
            
            # Oýun tapyldy!
            win_message = f"""🎉 Gutlaýarys, @{username}! Sen dogry sany tapdyň: {game['secret_number']}

👥 Gatnaşyjy sany: {len(game['participants'])}
🎯 Aralyk: 1-{game['max']}"""
            
            if game['flag']:
                win_message += f"\n🏴 {game['flag']}"
            
            bot.send_message(chat_id, win_message)
            
            # Oýuny aýyrmak
            del active_games[chat_id]
            
            # Bot eýesine habar bermek
            try:
                owner_win_message = f"""🏆 Oýun tamamlady!

💬 Çat: {message.chat.title or 'Şahsy çat'}
🏃 Tapan: @{username}
🎯 San: {game['secret_number']}
👥 Gatnaşyjy: {len(game['participants'])}"""
                bot.send_message(BOT_OWNER_ID, owner_win_message)
            except:
                print('Bot eýesine ýeňiş habary iberip bolmady')
        
        return
    
    # Gadagan sözleri barlamak
    if message_text and banned_words:
        lower_text = message_text.lower()
        for banned_word in banned_words:
            if banned_word in lower_text:
                try:
                    # Habary öçürmek
                    bot.delete_message(chat_id, message.message_id)
                    
                    # Duýduryş bermek
                    warning_msg = bot.send_message(
                        chat_id, 
                        f'⚠️ @{message.from_user.username or message.from_user.first_name}, gadagan söz ulanyp bolmaýar!'
                    )
                    
                    # 5 sekuntdan soň duýduryş habaryny öçürmek
                    def delete_warning():
                        time.sleep(5)
                        try:
                            bot.delete_message(chat_id, warning_msg.message_id)
                        except:
                            pass
                    
                   threading.Thread(target=delete_warning).start()
