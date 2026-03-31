import telebot
from telebot import types
import yt_dlp
import sqlite3
import re
import os
from datetime import datetime

# ===== НАСТРОЙКИ =====
BOT_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
ADMIN_ID = 5298604296

bot = telebot.TeleBot(BOT_TOKEN)

# ===== ПАПКА ДЛЯ ФАЙЛОВ (ВАЖНО ДЛЯ ХОСТИНГА) =====
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ===== БАЗА =====
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_seen TEXT,
                  referrer_id INTEGER,
                  ref_count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, 0)",
                  (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), referrer_id))

        if referrer_id and referrer_id != user_id:
            c.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?", (referrer_id,))

    conn.commit()
    conn.close()

def get_total():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    x = c.fetchone()[0]
    conn.close()
    return x

def get_refs(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT ref_count FROM users WHERE user_id=?", (user_id,))
    x = c.fetchone()
    conn.close()
    return x[0] if x else 0

init_db()

# ===== МЕНЮ =====
def menu(admin=False):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🎵 Поиск", "🆕 Новинки")
    if admin:
        m.add("📊 Статистика")
    return m

# ===== ФИЛЬТР =====
def valid(title):
    bad = ['mix', 'playlist', 'сборник', 'топ', 'лучшее', 'live']
    return not any(x in title.lower() for x in bad)

# ===== ПОИСК =====
def search(q):
    ydl_opts = {
        'quiet': True,
        'nocheckcertificate': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(f"ytsearch7:{q}", download=False)

        res = []
        for e in data['entries']:
            if not e:
                continue

            title = e.get('title')
            dur = e.get('duration', 0)

            if not title or not (60 <= dur <= 400):
                continue

            if not valid(title):
                continue

            res.append({
                'title': title,
                'url': e.get('webpage_url')
            })

        return res[:5]

    except Exception as e:
        print("SEARCH ERR:", e)
        return []

# ===== СКАЧКА (СТАБИЛЬНАЯ) =====
def download(url, title):
    safe = re.sub(r'[^\w\s-]', '', title)[:40]

    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': f'{DOWNLOAD_DIR}/{safe}.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0'
        },
        'geo_bypass': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# ===== ПАМЯТЬ =====
tracks_cache = {}

def show(chat_id, tracks, title):
    kb = types.InlineKeyboardMarkup()
    for i, t in enumerate(tracks):
        kb.add(types.InlineKeyboardButton(t['title'][:45], callback_data=f"p_{i}"))

    tracks_cache[chat_id] = tracks
    bot.send_message(chat_id, title, reply_markup=kb)

# ===== СТАРТ =====
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    username = msg.from_user.username or "none"

    ref = None
    args = msg.text.split()

    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            ref = int(args[1].split('_')[1])
        except:
            pass

    add_user(uid, username, ref)

    bot.send_message(msg.chat.id, "🎵 Бот готов", reply_markup=menu(uid == ADMIN_ID))

# ===== ПОИСК =====
@bot.message_handler(func=lambda m: m.text == "🎵 Поиск")
def s(msg):
    m = bot.send_message(msg.chat.id, "Напиши название:")
    bot.register_next_step_handler(m, s2)

def s2(msg):
    bot.send_message(msg.chat.id, "🔎 Ищу...")
    t = search(msg.text)

    if t:
        show(msg.chat.id, t, "Результаты")
    else:
        bot.send_message(msg.chat.id, "❌ Пусто")

# ===== НОВИНКИ =====
@bot.message_handler(func=lambda m: m.text == "🆕 Новинки")
def new(msg):
    bot.send_message(msg.chat.id, "🔎 Ищу новинки...")
    t = search("русские новинки музыка 2026")

    if t:
        show(msg.chat.id, t, "🆕 Новинки")
    else:
        bot.send_message(msg.chat.id, "❌ Нет")

# ===== СТАТА =====
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stat(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    total = get_total()
    refs = get_refs(ADMIN_ID)

    username = bot.get_me().username
    link = f"https://t.me/{username}?start=ref_{ADMIN_ID}"

    bot.send_message(msg.chat.id, f"""
👥 Пользователи: {total}
🔗 По рефке: {refs}

{link}
""")

# ===== СКАЧАТЬ =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("p_"))
def play(c):
    i = int(c.data.split("_")[1])
    t = tracks_cache.get(c.message.chat.id)

    if not t:
        return

    track = t[i]
    msg = bot.send_message(c.message.chat.id, "⏳ Качаю...")

    try:
        file = download(track['url'], track['title'])

        with open(file, 'rb') as f:
            bot.send_audio(c.message.chat.id, f, title=track['title'])

        os.remove(file)
        bot.delete_message(c.message.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ {e}", c.message.chat.id, msg.message_id)

# ===== ЗАПУСК =====
print("START")
bot.polling(none_stop=True)
