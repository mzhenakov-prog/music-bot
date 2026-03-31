import telebot
from telebot import types
import yt_dlp
import os
import re
import sqlite3
import time
from datetime import datetime

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
ADMIN_ID = 5298604296
BOT_USERNAME = 'reservettbot'
bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище результатов
user_tracks = {}

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_seen TEXT, ref_code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ref_links (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, label TEXT, clicks INTEGER DEFAULT 0, created_at TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, ref_code=None):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen, ref_code) VALUES (?, ?, ?, ?)", (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ref_code))
    if ref_code:
        c.execute("UPDATE ref_links SET clicks = clicks + 1 WHERE code = ?", (ref_code,))
    conn.commit()
    conn.close()

def add_ref_link(code, label):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO ref_links (code, label, created_at) VALUES (?, ?, ?)", (code, label, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_ref_links():
    conn = sqlite3.connect('music_bot.db')
    rows = conn.execute("SELECT code, label, clicks, created_at FROM ref_links ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def delete_ref_link(code):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM ref_links WHERE code = ?", (code,))
    conn.commit()
    conn.close()

init_db()

# ========== ПОИСК НА YOUTUBE ==========
def search_music(query):
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch',
        'extract_flat': True,
        'ignoreerrors': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch15:{query}", download=False)
            tracks = []
            if info and 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        title = entry.get('title', '')
                        duration = entry.get('duration', 0)
                        if duration and 60 <= duration <= 480:
                            tracks.append({
                                'title': title,
                                'url': f"https://youtube.com/watch?v={entry.get('id')}",
                                'duration': duration
                            })
            return tracks
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

# ========== СКАЧИВАНИЕ ==========
from pytube import YouTube

def download_audio(url, title):
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()[:50]
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).first()
        if not stream:
            raise Exception("Аудио не найдено")
        file = stream.download(filename=f"{safe_title}.mp4")
        return file
    except Exception as e:
        raise Exception(f"Ошибка: {e}")

def format_time(seconds):
    if not seconds:
        return "00:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"

# ========== ПОКАЗ ТРЕКОВ ==========
def show_tracks(chat_id, tracks, title, page=0):
    if not tracks:
        bot.send_message(chat_id, "❌ Ничего не найдено.")
        return
    
    per_page = 10
    total_pages = (len(tracks) + per_page - 1) // per_page
    start = page * per_page
    end = min(start + per_page, len(tracks))
    page_tracks = tracks[start:end]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, t in enumerate(page_tracks):
        idx = start + i
        dur = format_time(t['duration'])
        markup.add(types.InlineKeyboardButton(f"🎵 {t['title'][:45]} [{dur}]", callback_data=f"play_{idx}"))
    
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton("➡️ Далее", callback_data=f"page_{page+1}"))
    if nav:
        markup.add(*nav)
    
    user_tracks[chat_id] = tracks
    bot.send_message(chat_id, f"🎵 *{title}* (стр. {page+1}/{total_pages})", reply_markup=markup, parse_mode='Markdown')

# ========== КНОПКИ ==========
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Найти музыку", "🆕 Новинки")
    markup.add("🔗 Рефералка", "❓ Помощь")
    return markup

def ref_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Создать ссылку", callback_data="ref_create"))
    markup.add(types.InlineKeyboardButton("📊 Мои ссылки", callback_data="ref_list"))
    return markup

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    uname = message.from_user.username or "unknown"
    
    args = message.text.split()
    ref_code = None
    if len(args) > 1:
        ref_code = args[1]
    
    add_user(uid, uname, ref_code)
    
    bot.send_message(message.chat.id, "🎵 *Музыкальный бот готов!*", reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🎵 Найти музыку")
def search_cmd(message):
    bot.send_message(message.chat.id, "🔍 *Напиши название песни*", parse_mode='Markdown')
    bot.register_next_step_handler(message, do_search)

def do_search(message):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    tracks = search_music(message.text)
    
    if tracks:
        bot.delete_message(message.chat.id, wait.message_id)
        show_tracks(message.chat.id, tracks, f"Результаты: {message.text}")
    else:
        bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🆕 Новинки")
def new_cmd(message):
    wait = bot.send_message(message.chat.id, "🔎 *Загружаю новинки...*", parse_mode='Markdown')
    tracks = search_music("новинки музыки 2026")
    
    if tracks:
        bot.delete_message(message.chat.id, wait.message_id)
        show_tracks(message.chat.id, tracks, "🆕 Новинки")
    else:
        bot.edit_message_text("❌ Не удалось загрузить новинки.", message.chat.id, wait.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔗 Рефералка")
def ref_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только для создателя.")
        return
    
    bot.send_message(message.chat.id, "🔗 *Реферальная панель*", reply_markup=ref_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_cmd(message):
    help_text = """🎵 *Музыкальный бот*

🎵 *Найти музыку* — поиск по названию
🆕 *Новинки* — свежие треки
🔗 *Рефералка* — для создателя
❓ *Помощь* — это сообщение

*Как пользоваться:*
1. Нажми "Найти музыку"
2. Введи название
3. Выбери трек из списка
4. Бот скачает и отправит MP3

@avgustc"""
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu(), parse_mode='Markdown')

# ========== НАВИГАЦИЯ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_page(call):
    page = int(call.data.split('_')[1])
    tracks = user_tracks.get(call.message.chat.id)
    if not tracks:
        bot.answer_callback_query(call.id, "❌ Устарело")
        return
    
    title = call.message.text.split('*')[1] if '*' in call.message.text else "Результаты"
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_tracks(call.message.chat.id, tracks, title, page)

# ========== СКАЧИВАНИЕ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def play_track(call):
    idx = int(call.data.split('_')[1])
    tracks = user_tracks.get(call.message.chat.id)
    if not tracks or idx >= len(tracks):
        bot.answer_callback_query(call.id, "❌ Трек не найден")
        return
    
    track = tracks[idx]
    bot.answer_callback_query(call.id, "⏳ Скачиваю...")
    msg = bot.send_message(call.message.chat.id, f"🎵 *{track['title']}*\n⏳ Скачивание...", parse_mode='Markdown')
    
    try:
        file = download_audio(track['url'], track['title'])
        with open(file, 'rb') as f:
            bot.send_audio(
                call.message.chat.id,
                f,
                title=track['title'],
                caption=f"🎵 *{track['title']}*\n\n📥 Скачано с @{BOT_USERNAME}"
            )
        os.remove(file)
        bot.delete_message(call.message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {str(e)[:100]}", call.message.chat.id, msg.message_id, parse_mode='Markdown')

# ========== РЕФЕРАЛЬНЫЕ КНОПКИ ==========
@bot.callback_query_handler(func=lambda call: call.data == "ref_create")
def create_ref(call):
    if call.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(call.message.chat.id, "📝 *Введи название для ссылки*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, save_ref)

def save_ref(message):
    label = message.text.strip()
    code = f"ref_{int(time.time())}"
    add_ref_link(code, label)
    ref_link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(message.chat.id, f"✅ *Ссылка создана!*\n\n🔗 `{ref_link}`\n📌 Метка: {label}", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "ref_list")
def list_refs(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    links = get_ref_links()
    if not links:
        bot.send_message(call.message.chat.id, "📭 *Нет созданных ссылок*", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for code, label, clicks, created in links:
        markup.add(types.InlineKeyboardButton(f"📊 {label} — {clicks} переходов", callback_data=f"ref_{code}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_ref"))
    bot.send_message(call.message.chat.id, "📊 *Список реферальных ссылок:*", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('ref_') and call.data != "ref_create" and call.data != "ref_list")
def show_ref_stats(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    code = call.data[4:]
    links = get_ref_links()
    for c, label, clicks, created in links:
        if c == code:
            ref_link = f"https://t.me/{BOT_USERNAME}?start={code}"
            text = f"📊 *Статистика ссылки*\n\n📌 Метка: {label}\n🔗 `{ref_link}`\n👥 Переходов: {clicks}\n📅 Создана: {created}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🗑 Удалить", callback_data=f"del_{code}"))
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="ref_list"))
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def delete_ref(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    code = call.data[4:]
    delete_ref_link(code)
    bot.answer_callback_query(call.id, "✅ Ссылка удалена!")
    bot.edit_message_text("🗑 Ссылка удалена", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_ref")
def back_to_ref(call):
    if call.from_user.id != ADMIN_ID:
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    ref_cmd(call.message)

if __name__ == '__main__':
    print("🎵 Музыкальный бот запущен!")
    bot.infinity_polling()
