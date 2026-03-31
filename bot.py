import telebot
from telebot import types
import yt_dlp
import os
import re
import sqlite3
import time
from datetime import datetime

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
ADMIN_ID = 5298604296
BOT_USERNAME = 'reservettbot'

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище для результатов поиска
user_data = {}

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_seen TEXT, ref_code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ref_links 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, label TEXT, clicks INTEGER DEFAULT 0, created_at TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, ref_code=None):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen, ref_code) VALUES (?, ?, ?, ?)", 
              (user_id, username, datetime.now().strftime("%d.%m.%Y"), ref_code))
    if ref_code:
        c.execute("UPDATE ref_links SET clicks = clicks + 1 WHERE code = ?", (ref_code,))
    conn.commit()
    conn.close()

def add_ref_link(code, label):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO ref_links (code, label, created_at) VALUES (?, ?, ?)", 
              (code, label, datetime.now().strftime("%d.%m.%Y")))
    conn.commit()
    conn.close()

def get_ref_links():
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    rows = c.execute("SELECT label, clicks FROM ref_links ORDER BY id DESC").fetchall()
    conn.close()
    return rows

init_db()

# ========== ПОИСК МУЗЫКИ (улучшенный) ==========
def search_music(query):
    """Поиск треков на YouTube с фильтрацией"""
    # Убираем мусорные слова
    search_query = f"{query} audio -mix -сборник -album -live -remix -cover"
    
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch',
        'extract_flat': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Запрашиваем 30 результатов
            info = ydl.extract_info(f"ytsearch30:{search_query}", download=False)
            tracks = []
            
            if info and 'entries' in info:
                for entry in info['entries']:
                    if not entry:
                        continue
                    
                    title = entry.get('title', '')
                    duration = entry.get('duration', 0)
                    
                    # Фильтрация
                    if not duration or duration < 60 or duration > 480:
                        continue
                    
                    # Исключаем сборники и миксы
                    title_lower = title.lower()
                    bad_words = ['playlist', 'mix', 'сборник', 'плейлист', 'album', 'live', 'remix', 'cover']
                    if any(word in title_lower for word in bad_words):
                        continue
                    
                    tracks.append({
                        'title': title,
                        'url': f"https://youtube.com/watch?v={entry.get('id')}",
                        'duration': duration
                    })
                    
                    if len(tracks) >= 20:
                        break
            
            return tracks
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

def download_audio(url, title):
    """Скачивание MP3"""
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()[:50]
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': safe_title,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return f"{safe_title}.mp3"

def format_time(seconds):
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"

# ========== ОТОБРАЖЕНИЕ СТРАНИЦ ==========
def render_page(chat_id, page=0):
    data = user_data.get(chat_id)
    if not data:
        return None, None
    
    tracks = data['tracks']
    per_page = 10
    total_pages = (len(tracks) + per_page - 1) // per_page
    total_pages = min(total_pages, 6)
    
    start = page * per_page
    end = min(start + per_page, len(tracks))
    page_tracks = tracks[start:end]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, t in enumerate(page_tracks):
        idx = start + i
        dur = format_time(t['duration'])
        title = t['title'][:45]
        markup.add(types.InlineKeyboardButton(f"🎵 {title} [{dur}]", callback_data=f"dl_{idx}"))
    
    # Кнопки навигации
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton("➡️ Далее", callback_data=f"page_{page+1}"))
    if nav:
        markup.row(*nav)
    
    text = f"🎵 *{data['title']}* (стр. {page+1}/{total_pages})"
    return text, markup

# ========== КНОПКИ МЕНЮ ==========
def get_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Найти музыку", "🆕 Новинки")
    if is_admin:
        markup.add("🔗 Рефералка")
    markup.add("❓ Помощь")
    return markup

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start_cmd(message):
    ref = None
    args = message.text.split()
    if len(args) > 1:
        ref = args[1]
    
    add_user(message.from_user.id, message.from_user.username, ref)
    
    is_admin = (message.from_user.id == ADMIN_ID)
    welcome = "🎵 *Музыкальный бот готов!*\n\nИспользуй кнопки внизу."
    bot.send_message(message.chat.id, welcome, reply_markup=get_menu(is_admin), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🎵 Найти музыку")
def search_cmd(message):
    msg = bot.send_message(message.chat.id, "🔍 *Напиши название песни или исполнителя*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, do_search)

def do_search(message):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    tracks = search_music(message.text)
    bot.delete_message(message.chat.id, wait.message_id)
    
    if not tracks:
        bot.send_message(message.chat.id, "❌ Ничего не найдено. Попробуй другой запрос.")
        return
    
    user_data[message.chat.id] = {
        'tracks': tracks,
        'title': f"Результаты: {message.text}",
        'page': 0
    }
    text, markup = render_page(message.chat.id, 0)
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🆕 Новинки")
def new_cmd(message):
    wait = bot.send_message(message.chat.id, "🔎 *Загружаю новинки...*", parse_mode='Markdown')
    tracks = search_music("новинки музыки 2026 российская")
    bot.delete_message(message.chat.id, wait.message_id)
    
    if not tracks:
        bot.send_message(message.chat.id, "❌ Не удалось загрузить новинки.")
        return
    
    user_data[message.chat.id] = {
        'tracks': tracks,
        'title': "🆕 Новинки",
        'page': 0
    }
    text, markup = render_page(message.chat.id, 0)
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔗 Рефералка")
def ref_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только для создателя.")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Создать ссылку", callback_data="ref_create"))
    markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="ref_stats"))
    bot.send_message(message.chat.id, "🔗 *Реферальная панель*", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_cmd(message):
    is_admin = (message.from_user.id == ADMIN_ID)
    text = """🎵 *Музыкальный бот*

🎵 *Найти музыку* — поиск по названию
🆕 *Новинки* — свежие треки
❓ *Помощь* — это сообщение

*Как пользоваться:*
1. Нажми "Найти музыку"
2. Введи название
3. Выбери трек из списка
4. Бот скачает и отправит MP3

*По вопросам:* @avgustc"""
    
    if is_admin:
        text += "\n\n🔗 *Рефералка* — создавай ссылки для отслеживания"
    
    bot.send_message(message.chat.id, text, reply_markup=get_menu(is_admin), parse_mode='Markdown')

# ========== CALLBACK-ОБРАБОТЧИКИ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_page(call):
    page = int(call.data.split('_')[1])
    text, markup = render_page(call.message.chat.id, page)
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                          reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def download_track(call):
    idx = int(call.data.split('_')[1])
    data = user_data.get(call.message.chat.id)
    if not data or idx >= len(data['tracks']):
        bot.answer_callback_query(call.id, "❌ Трек не найден")
        return
    
    track = data['tracks'][idx]
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

@bot.callback_query_handler(func=lambda call: call.data == "ref_create")
def create_ref(call):
    msg = bot.send_message(call.message.chat.id, "📝 *Введи название для ссылки*\n\nНапример: `telegram_канал`", parse_mode='Markdown')
    bot.register_next_step_handler(msg, save_ref)

def save_ref(message):
    label = message.text.strip()
    code = f"ref_{int(time.time())}"
    add_ref_link(code, label)
    
    ref_link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(message.chat.id, f"✅ *Ссылка создана!*\n\n🔗 `{ref_link}`\n📌 Метка: {label}", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "ref_stats")
def show_stats(call):
    links = get_ref_links()
    if not links:
        bot.send_message(call.message.chat.id, "📭 *Нет созданных ссылок*", parse_mode='Markdown')
        return
    
    text = "📊 *Статистика переходов:*\n\n"
    for label, clicks in links:
        text += f"🔸 *{label}*: {clicks} переходов\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

if __name__ == '__main__':
    print("🎵 Музыкальный бот запущен!")
    bot.infinity_polling()
