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

# Временное хранилище для страниц поиска
user_data = {} 

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect('music_bot.db', check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, username TEXT, first_seen TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS ref_links 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, label TEXT, clicks INTEGER DEFAULT 0, created_at TEXT)''')
        conn.commit()

def add_user(user_id, username, ref_code=None):
    with sqlite3.connect('music_bot.db') as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen) VALUES (?, ?, ?)", 
                  (user_id, username, datetime.now().strftime("%d.%m.%Y")))
        if ref_code:
            c.execute("UPDATE ref_links SET clicks = clicks + 1 WHERE code = ?", (ref_code,))
        conn.commit()

# --- МОЩНЫЙ ПОИСК ---
def get_music_data(query):
    # Убираем мусор, но оставляем пространство для маневра парсеру
    search_query = f"{query} -mix -сборник -album"
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch80', # Запрашиваем больше, чтобы после фильтра осталось много
        'extract_flat': True,
        'nocheckcertificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch80:{search_query}", download=False)
            results = []
            if 'entries' in info:
                for e in info['entries']:
                    if e:
                        d = e.get('duration')
                        # ФИЛЬТР: От 60 до 480 секунд (1-8 минут)
                        if d and 60 <= d <= 480:
                            results.append({
                                'title': e.get('title', 'Без названия'),
                                'url': e.get('url') or e.get('webpage_url'),
                                'duration': d
                            })
            return results
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

def download_track(url, title):
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

# --- ИНТЕРФЕЙС СТРАНИЦ ---
def render_page(chat_id, page=0):
    data = user_data.get(chat_id)
    if not data: return
    
    tracks = data['tracks']
    per_page = 10
    total_pages = (len(tracks) - 1) // per_page + 1
    # Ограничиваем до 6 страниц, как просил
    total_pages = min(total_pages, 6)
    
    start = page * per_page
    end = start + per_page
    current_tracks = tracks[start:end]

    markup = types.InlineKeyboardMarkup()
    for i, t in enumerate(current_tracks):
        dur = f"{t['duration']//60}:{t['duration']%60:02d}"
        markup.add(types.InlineKeyboardButton(f"{t['title'][:35]} [{dur}]", callback_data=f"dl_{start+i}"))
    
    # Кнопки навигации
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_{page-1}"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"nav_{page+1}"))
    
    if nav: markup.row(*nav)
    
    text = f"🎵 *Результаты поиска:* {data['query']}\n📄 Страница {page+1} из {total_pages}"
    return text, markup

# --- ОБРАБОТЧИКИ ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    ref = m.text.split()[1] if len(m.text.split()) > 1 else None
    add_user(m.from_user.id, m.from_user.username, ref)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Найти музыку", "🆕 Новинки")
    if m.from_user.id == ADMIN_ID: markup.add("🔗 Рефералка")
    bot.send_message(m.chat.id, "✌️ Привет! Готов искать музыку без лишних миксов.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎵 Найти музыку")
def search_init(m):
    msg = bot.send_message(m.chat.id, "🎹 Введи название (артист, песня):")
    bot.register_next_step_handler(msg, perform_search)

def perform_search(m):
    query = m.text
    wait = bot.send_message(m.chat.id, "🔎 Ищу треки (1-8 мин)...")
    tracks = get_music_data(query)
    bot.delete_message(m.chat.id, wait.message_id)
    
    if not tracks:
        bot.send_message(m.chat.id, "😭 Ничего не нашлось. Попробуй другое название.")
        return
    
    user_data[m.chat.id] = {'query': query, 'tracks': tracks, 'page': 0}
    text, markup = render_page(m.chat.id, 0)
    bot.send_message(m.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('nav_'))
def change_page(c):
    page = int(c.data.split('_')[1])
    text, markup = render_page(c.message.chat.id, page)
    bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('dl_'))
def download_call(c):
    idx = int(c.data.split('_')[1])
    track = user_data[c.message.chat.id]['tracks'][idx]
    bot.answer_callback_query(c.id, "🚀 Загружаю трек...")
    try:
        f_path = download_track(track['url'], track['title'])
        with open(f_path, 'rb') as f:
            bot.send_audio(c.message.chat.id, f, title=track['title'], caption=f"@{BOT_USERNAME}")
        os.remove(f_path)
    except:
        bot.send_message(c.message.chat.id, "❌ Ошибка скачивания.")

@bot.message_handler(func=lambda m: m.text == "🆕 Новинки")
def news_search(m):
    wait = bot.send_message(m.chat.id, "🔥 Загружаю свежие новинки России...")
    # Автоматический поиск актуального чарта
    tracks = get_music_data("Новинки музыки 2024 2025") 
    bot.delete_message(m.chat.id, wait.message_id)
    
    user_data[m.chat.id] = {'query': "Новинки РФ", 'tracks': tracks, 'page': 0}
    text, markup = render_page(m.chat.id, 0)
    bot.send_message(m.chat.id, text, reply_markup=markup, parse_mode='Markdown')

# --- РЕФЕРАЛКА ---
@bot.message_handler(func=lambda m: m.text == "🔗 Рефералка" and m.from_user.id == ADMIN_ID)
def ref_admin(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Создать ссылку", callback_data="ref_gen"))
    markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="ref_stat"))
    bot.send_message(m.chat.id, "💎 Админ-панель ссылок:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "ref_gen")
def ref_gen(c):
    msg = bot.send_message(c.message.chat.id, "Введите название для метки (напр. 'v_pablika_1'):")
    bot.register_next_step_handler(msg, ref_save)

def ref_save(m):
    label = m.text
    code = f"promo{int(time.time())}"
    with sqlite3.connect('music_bot.db') as conn:
        conn.execute("INSERT INTO ref_links (code, label, created_at) VALUES (?, ?, ?)", 
                     (code, label, datetime.now().strftime("%d.%m")))
    bot.send_message(m.chat.id, f"✅ Ссылка для {label}:\nhttps://t.me/{BOT_USERNAME}?start={code}")

@bot.callback_query_handler(func=lambda c: c.data == "ref_stat")
def ref_stat(c):
    with sqlite3.connect('music_bot.db') as conn:
        rows = conn.execute("SELECT label, clicks FROM ref_links").fetchall()
    text = "📊 Статистика:\n\n" + "\n".join([f"🔸 {r[0]}: {r[1]} чел." for r in rows])
    bot.send_message(c.message.chat.id, text)

if __name__ == '__main__':
    init_db()
    bot.infinity_polling()
