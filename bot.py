import telebot
from telebot import types
import yt_dlp
import sqlite3
import re
import os
from datetime import datetime

# ===== НАСТРОЙКИ =====
BOT_TOKEN = 'ТВОЙ_ТОКЕН_СЮДА'
ADMIN_ID = 5298604296

bot = telebot.TeleBot(BOT_TOKEN)

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_seen TEXT,
            referrer_id INTEGER,
            ref_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = c.fetchone()

    if not exists:
        c.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, 0)",
            (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), referrer_id)
        )

        if referrer_id and referrer_id != user_id:
            c.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?", (referrer_id,))

    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_ref_count(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT ref_count FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

init_db()

# ===== МЕНЮ =====
def main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Поиск", "🆕 Новинки")

    if is_admin:
        markup.add("📊 Статистика")

    return markup

# ===== ФИЛЬТР МУСОРА =====
def is_valid(title):
    bad = [
        'mix', 'playlist', 'сборник', 'топ',
        'лучшее', '1 hour', 'час', 'live', 'remix'
    ]
    title = title.lower()
    return not any(x in title for x in bad)

# ===== ПОИСК =====
def search_tracks(query):
    ydl_opts = {'quiet': True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch10:{query}", download=False)

    results = []
    for e in info.get('entries', []):
        if not e:
            continue

        title = e.get('title')
        duration = e.get('duration', 0)

        if not title or not (60 <= duration <= 400):
            continue

        if not is_valid(title):
            continue

        results.append({
            'title': title,
            'url': e.get('webpage_url')
        })

    return results[:5]

# ===== СКАЧИВАНИЕ =====
def download(url, title):
    safe = re.sub(r'[^\w\s-]', '', title)[:40]

    opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{safe}.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0'
        }
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# ===== ХРАНЕНИЕ =====
user_tracks = {}

# ===== ПОКАЗ =====
def show_tracks(chat_id, tracks, title):
    markup = types.InlineKeyboardMarkup()

    for i, t in enumerate(tracks):
        markup.add(types.InlineKeyboardButton(
            text=t['title'][:50],
            callback_data=f"play_{i}"
        ))

    user_tracks[chat_id] = tracks
    bot.send_message(chat_id, f"🎵 {title}", reply_markup=markup)

# ===== СТАРТ =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "none"

    ref = None
    args = message.text.split()

    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            ref = int(args[1].split('_')[1])
        except:
            pass

    add_user(user_id, username, ref)

    bot.send_message(
        message.chat.id,
        "🎵 Бот готов. Выбирай:",
        reply_markup=main_menu(user_id == ADMIN_ID)
    )

# ===== ПОИСК =====
@bot.message_handler(func=lambda m: m.text == "🎵 Поиск")
def search_cmd(message):
    msg = bot.send_message(message.chat.id, "Напиши название:")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    bot.send_message(message.chat.id, "🔎 Ищу...")

    tracks = search_tracks(message.text)

    if tracks:
        show_tracks(message.chat.id, tracks, "Результаты")
    else:
        bot.send_message(message.chat.id, "❌ Ничего не найдено")

# ===== НОВИНКИ =====
@bot.message_handler(func=lambda m: m.text == "🆕 Новинки")
def new_cmd(message):
    bot.send_message(message.chat.id, "🔎 Ищу новинки...")

    tracks = search_tracks("русская музыка новинки 2026")

    if tracks:
        show_tracks(message.chat.id, tracks, "🆕 Новинки")
    else:
        bot.send_message(message.chat.id, "❌ Не найдено")

# ===== СТАТИСТИКА =====
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    total = get_total_users()
    ref = get_ref_count(ADMIN_ID)

    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start=ref_{ADMIN_ID}"

    bot.send_message(message.chat.id, f"""
📊 Пользователи: {total}
🔗 По рефке: {ref}

Твоя ссылка:
{link}
""")

# ===== СКАЧАТЬ =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("play_"))
def play(call):
    idx = int(call.data.split("_")[1])
    tracks = user_tracks.get(call.message.chat.id)

    if not tracks:
        return

    track = tracks[idx]

    msg = bot.send_message(call.message.chat.id, "⏳ Скачиваю...")

    try:
        file = download(track['url'], track['title'])

        with open(file, 'rb') as f:
            bot.send_audio(call.message.chat.id, f, title=track['title'])

        os.remove(file)
        bot.delete_message(call.message.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, msg.message_id)

# ===== ЗАПУСК =====
print("Бот запущен...")
bot.polling(none_stop=True)
