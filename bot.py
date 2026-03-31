import telebot
from telebot import types
import yt_dlp
import os
import re
import sqlite3
import time
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
ADMIN_ID = 5298604296
BOT_USERNAME = 'reservettbot'

bot = telebot.TeleBot(BOT_TOKEN)

# Глобальное хранилище для результатов поиска (в памяти для скорости)
search_cache = {}

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect('music_bot.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, username TEXT, first_seen TEXT, referrer_id INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS ref_links 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, label TEXT, clicks INTEGER DEFAULT 0, created_at TEXT)''')
        conn.commit()

def add_user(user_id, username, ref_code=None):
    with sqlite3.connect('music_bot.db') as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen) VALUES (?, ?, ?)", 
                  (user_id, username, datetime.now().strftime("%Y-%m-%d")))
        if ref_code:
            c.execute("UPDATE ref_links SET clicks = clicks + 1 WHERE code = ?", (ref_code,))
        conn.commit()

init_db()

# --- ПОИСК И ФИЛЬТРАЦИЯ ---
def search_music(query):
    # Исключаем мусор прямо в запросе
    clean_query = f"{query} -mix -сборник -hits -full album -1 hour"
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch60', # Ищем 60 вариантов для пагинации
        'extract_flat': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch60:{clean_query}", download=False)
            tracks = []
            if 'entries' in info:
                for e in info['entries']:
                    if e:
                        dur = e.get('duration')
                        # ФИЛЬТР: От 1 до 8 минут (60-480 сек)
                        if dur and 60 <= dur <= 480:
                            tracks.append({
                                'title': e.get('title', 'Unknown'),
                                'url': e.get('url') or e.get('webpage_url'),
                                'duration': dur
                            })
            return tracks
    except: return []

def download_audio(url, title):
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()[:50]
    filename = f"{safe_title}.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': safe_title,
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return f"{safe_title}.mp3"

# --- КЛАВИАТУРЫ ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Найти музыку", "🆕 Новинки")
    if uid == ADMIN_ID: markup.add("🔗 Рефералка")
    markup.add("❓ Помощь")
    return markup

def admin_ref_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Создать ссылку", callback_data="admin_create_ref"))
    markup.add(types.InlineKeyboardButton("📊 Статистика ссылок", callback_data="admin_stats_ref"))
    return markup

# --- ОБРАБОТКА ПОИСКА И ПАГИНАЦИИ ---
def send_search_page(chat_id, query, page=0):
    tracks = search_cache.get(chat_id, {}).get('tracks', [])
    per_page = 10
    total_pages = (len(tracks) - 1) // per_page + 1
    
    if not tracks:
        bot.send_message(chat_id, "❌ Ничего не найдено по фильтрам (1-8 мин).")
        return

    markup = types.InlineKeyboardMarkup()
    start = page * per_page
    end = start + per_page
    
    for i, t in enumerate(tracks[start:end]):
        dur = f"{t['duration']//60}:{t['duration']%60:02d}"
        markup.add(types.InlineKeyboardButton(f"{t['title'][:40]} [{dur}]", callback_data=f"dl_{start+i}"))
    
    # Кнопки навигации
    nav_btns = []
    if page > 0:
        nav_btns.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
    if page < total_pages - 1 and page < 5: # Ограничение до 6 страниц
        nav_btns.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))
    
    if nav_btns: markup.row(*nav_btns)
    
    msg_text = f"🔎 Результаты по запросу: *{query}*\nСтр: {page+1}/{min(total_pages, 6)}"
    bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode='Markdown')

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(m):
    ref_code = m.text.split()[1] if len(m.text.split()) > 1 else None
    add_user(m.from_user.id, m.from_user.username, ref_code)
    bot.send_message(m.chat.id, "🚀 Бот готов к поиску музыки!", reply_markup=main_menu(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🎵 Найти музыку")
def ask_search(m):
    msg = bot.send_message(m.chat.id, "Введите название трека:")
    bot.register_next_step_handler(msg, do_search)

def do_search(m):
    query = m.text
    wait = bot.send_message(m.chat.id, "🔎 Ищу и фильтрую треки...")
    tracks = search_music(query)
    bot.delete_message(m.chat.id, wait.message_id)
    
    search_cache[m.chat.id] = {'query': query, 'tracks': tracks}
    send_search_page(m.chat.id, query, 0)

@bot.callback_query_handler(func=lambda c: c.data.startswith('page_'))
def handle_page(c):
    page = int(c.data.split('_')[1])
    query = search_cache.get(c.message.chat.id, {}).get('query', 'Поиск')
    bot.delete_message(c.message.chat.id, c.message.message_id)
    send_search_page(c.message.chat.id, query, page)

@bot.callback_query_handler(func=lambda c: c.data.startswith('dl_'))
def handle_dl(c):
    idx = int(c.data.split('_')[1])
    track = search_cache.get(c.message.chat.id, {}).get('tracks', [])[idx]
    bot.answer_callback_query(c.id, "⏳ Скачиваю...")
    try:
        path = download_audio(track['url'], track['title'])
        with open(path, 'rb') as f:
            bot.send_audio(c.message.chat.id, f, title=track['title'], caption=f"@{BOT_USERNAME}")
        os.remove(path)
    except Exception as e:
        bot.send_message(c.message.chat.id, "❌ Ошибка загрузки.")

# --- РЕФЕРАЛКА (АДМИНКА) ---
@bot.message_handler(func=lambda m: m.text == "🔗 Рефералка" and m.from_user.id == ADMIN_ID)
def admin_ref(m):
    bot.send_message(m.chat.id, "💎 Управление рекламой и ссылками:", reply_markup=admin_ref_menu())

@bot.callback_query_handler(func=lambda c: c.data == "admin_create_ref")
def create_ref_step1(c):
    msg = bot.send_message(c.message.chat.id, "Введите название для ссылки (например: 'reklama_marta'):")
    bot.register_next_step_handler(msg, create_ref_step2)

def create_ref_step2(m):
    label = m.text
    code = f"ad_{int(time.time())}"
    with sqlite3.connect('music_bot.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO ref_links (code, label, created_at) VALUES (?, ?, ?)", 
                  (code, label, datetime.now().strftime("%d.%m.%Y")))
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(m.chat.id, f"✅ Ссылка создана для: *{label}*\n\n`{link}`", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data == "admin_stats_ref")
def stats_ref(c):
    with sqlite3.connect('music_bot.db') as conn:
        c = conn.cursor()
        c.execute("SELECT label, clicks, created_at FROM ref_links")
        rows = c.fetchall()
    
    if not rows:
        bot.send_message(c.message.chat.id, "Ссылок пока нет.")
        return
        
    text = "📊 *Статистика переходов:*\n\n"
    for row in rows:
        text += f"📍 {row[0]} | Кликнули: {row[1]} | Дата: {row[2]}\n"
    bot.send_message(c.message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🆕 Новинки")
def news(m):
    # Самые свежие треки (можно менять этот список)
    tracks = ["Инстасамка - Пампим", "MACAN - IVL", "Miyagi - По полям", "Friendly Thug 52 - No Love"]
    markup = types.InlineKeyboardMarkup()
    for t in tracks:
        markup.add(types.InlineKeyboardButton(f"🔥 {t}", callback_data=f"news_search_{t[:15]}"))
    bot.send_message(m.chat.id, "🇷🇺 Свежие новинки России:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('news_search_'))
def news_search_call(c):
    q = c.data.replace('news_search_', '')
    bot.send_message(c.message.chat.id, f"Ищу новинку: {q}...")
    # Здесь можно вызвать do_search программно

if __name__ == '__main__':
    bot.infinity_polling()
