import telebot
from telebot import types
import yt_dlp
import os
import re
import sqlite3
import time
from datetime import datetime

# КОНФИГ
BOT_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
ADMIN_ID = 5298604296
BOT_USERNAME = 'reservettbot'

bot = telebot.TeleBot(BOT_TOKEN)

# --- БАЗА ДАННЫХ (РЕФЕРАЛКА) ---
def init_db():
    conn = sqlite3.connect('music_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_seen TEXT, referrer_id INTEGER, ref_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ref_links 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, user_id INTEGER, created_by INTEGER, created_at TEXT, clicks INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    with sqlite3.connect('music_bot.db') as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen, referrer_id) VALUES (?, ?, ?, ?)", 
                  (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), referrer_id))
        if referrer_id and referrer_id != user_id:
            c.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?", (referrer_id,))
        conn.commit()

# --- ПОИСК С ФИЛЬТРАМИ (ДО 7 МИНУТ) ---
def search_music(query):
    # Добавляем исключения прямо в запрос для точности
    clean_query = f"{query} -mix -сборник -hits -full album -1 hour"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch15',
        'extract_flat': True,
        'nocheckcertificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch15:{clean_query}", download=False)
            tracks = []
            
            if 'entries' in info:
                for e in info['entries']:
                    if e:
                        duration = e.get('duration')
                        title = e.get('title', '').lower()
                        
                        # ФИЛЬТР: Длина от 30 сек до 420 сек (7 минут) 
                        # + доп. проверка на стоп-слова в названии
                        if duration and 30 <= duration <= 420:
                            stop_words = ['сборник', 'full album', 'mix', 'сборка', '1 hour', '2 hours']
                            if not any(word in title for word in stop_words):
                                tracks.append({
                                    'title': e.get('title', 'Без названия'),
                                    'url': e.get('url') or e.get('webpage_url'),
                                    'duration': duration
                                })
            return tracks
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

def download_audio(url, title):
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()[:50]
    filename = f"{safe_title}.mp3"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': safe_title,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    return f"{safe_title}.mp3" if os.path.exists(f"{safe_title}.mp3") else None

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Найти музыку", "🆕 Новинки")
    if user_id == ADMIN_ID:
        markup.add("🔗 Рефералка")
    markup.add("❓ Помощь")
    return markup

# --- ОБРАБОТЧИКИ ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    uname = m.from_user.username or "user"
    
    ref_id = None
    if len(m.text.split()) > 1:
        code = m.text.split()[1]
        with sqlite3.connect('music_bot.db') as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM ref_links WHERE code = ?", (code,))
            row = c.fetchone()
            if row:
                ref_id = row[0]
                c.execute("UPDATE ref_links SET clicks = clicks + 1 WHERE code = ?", (code,))
    
    add_user(uid, uname, ref_id)
    bot.send_message(m.chat.id, "🎵 *Музыкальный бот к твоим услугам!*", 
                     reply_markup=main_menu(uid), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🎵 Найти музыку")
def ask_search(m):
    msg = bot.send_message(m.chat.id, "🔍 *Напиши название песни или артиста:*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_search)

def process_search(m):
    query = m.text
    wait_msg = bot.send_message(m.chat.id, "🔎 *Ищу лучшие варианты...*", parse_mode='Markdown')
    
    tracks = search_music(query)
    bot.delete_message(m.chat.id, wait_msg.message_id)
    
    if not tracks:
        bot.send_message(m.chat.id, "❌ *Ничего не найдено (до 7 минут).* Попробуй уточнить запрос.", parse_mode='Markdown')
        return

    global user_temp_results
    if 'user_temp_results' not in globals(): user_temp_results = {}
    user_temp_results[m.chat.id] = tracks

    markup = types.InlineKeyboardMarkup()
    for i, t in enumerate(tracks[:10]):
        dur = f"{t['duration']//60}:{t['duration']%60:02d}"
        markup.add(types.InlineKeyboardButton(f"🎵 {t['title'][:40]} [{dur}]", callback_data=f"dl_{i}"))
    
    bot.send_message(m.chat.id, f"🎶 *Результаты для:* {query}", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def handle_download(call):
    idx = int(call.data.split('_')[1])
    tracks = user_temp_results.get(call.message.chat.id)
    
    if not tracks:
        bot.answer_callback_query(call.id, "❌ Ошибка: данные устарели")
        return
        
    track = tracks[idx]
    bot.answer_callback_query(call.id, "⏳ Скачиваю...")
    
    try:
        file_path = download_audio(track['url'], track['title'])
        if file_path:
            with open(file_path, 'rb') as audio:
                bot.send_audio(call.message.chat.id, audio, title=track['title'], 
                               caption=f"✅ *{track['title']}*\n📥 Скачано через @{BOT_USERNAME}", parse_mode='Markdown')
            os.remove(file_path)
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка файла")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Ошибка: {str(e)[:50]}")

@bot.message_handler(func=lambda m: m.text == "🆕 Новинки")
def news_tracks(m):
    # Новинки из твоего списка
    tracks = [
        "SMS - UncleFlexxx", "Тону - HOLLYFLAME", "КУКЛА Remix 2026 - Дискотека Авария",
        "Плакала надежда - Jakone, Kiliana", "NOBODY - Aarne, Toxi$, Big Baby Tape"
    ]
    markup = types.InlineKeyboardMarkup()
    for t in tracks:
        # При нажатии бот просто отправит этот текст, чтобы сработал поиск
        markup.add(types.InlineKeyboardButton(f"🔥 {t}", callback_data=f"search_new_{t[:20]}"))
    bot.send_message(m.chat.id, "✨ *Свежие хиты недели:*", reply_markup=markup, parse_mode='Markdown')

# Админ-команда для рефки
@bot.message_handler(commands=['create_ref'])
def create_ref_cmd(m):
    if m.from_user.id != ADMIN_ID: return
    try:
        target_id = m.text.split()[1]
        code = f"ref_{target_id}_{int(time.time())}"
        with sqlite3.connect('music_bot.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO ref_links (code, user_id, created_by, created_at) VALUES (?, ?, ?, ?)", 
                      (code, target_id, ADMIN_ID, datetime.now().strftime("%Y-%m-%d")))
        link = f"https://t.me/{bot.get_me().username}?start={code}"
        bot.send_message(m.chat.id, f"✅ Ссылка создана:\n`{link}`", parse_mode='Markdown')
    except:
        bot.send_message(m.chat.id, "❌ Используй: `/create_ref ID`", parse_mode='Markdown')

if __name__ == '__main__':
    init_db()
    print("🎵 Бот успешно запущен на твоем токене!")
    bot.infinity_polling()
