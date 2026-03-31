import telebot
from telebot import types
import yt_dlp
import os
import re
import random
import time
import sqlite3
from datetime import datetime

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
ADMIN_ID = 5298604296
BOT_USERNAME = 'muz_super_music_bot'  # 👈 ЗАМЕНИ НА USERNAME БОТА (без @)
bot = telebot.TeleBot(BOT_TOKEN)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_seen TEXT,
                  referrer_id INTEGER,
                  ref_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ref_links
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  code TEXT UNIQUE,
                  user_id INTEGER,
                  created_by INTEGER,
                  created_at TEXT,
                  clicks INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen, referrer_id) VALUES (?, ?, ?, ?)",
              (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), referrer_id))
    if referrer_id and referrer_id != user_id:
        c.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?", (referrer_id,))
    conn.commit()
    conn.close()

def add_ref_link(code, user_id, created_by):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO ref_links (code, user_id, created_by, created_at) VALUES (?, ?, ?, ?)",
              (code, user_id, created_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_ref_links(created_by):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("SELECT id, code, user_id, created_at, clicks FROM ref_links WHERE created_by = ? ORDER BY id DESC", (created_by,))
    links = c.fetchall()
    conn.close()
    return links

def click_ref_link(code):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("UPDATE ref_links SET clicks = clicks + 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def get_ref_stats(user_id):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("SELECT ref_count FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_total_users():
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

init_db()

# ========== НОВИНКИ ==========
NEW_TRACKS = [
    "SMS - UncleFlexxx", "Тону - HOLLYFLAME", "КУКЛА Remix 2026 - Дискотека Авария, VONAMOUR",
    "Плакала надежда - Jakone, Kiliana, Любовь Успенская", "NOBODY - Aarne, Toxi$, Big Baby Tape",
    "Гаснет свет - Nasty Babe", "КУПЕР - SQWOZ BAB", "БАНК - ICEGERGERT, Zivert",
    "Цыганка нагадала - Artem Smile", "Феникс - BEARWOLF", "Жиганская - Jakone, Kiliana",
    "Сыпь, гармоника! - СДП", "G-Woman - ICEGERGERT", "Дэнс - 9 Грамм",
    "Сердце - Альберт Назранов", "На мурмулях - Это Радио", "Tom Ford - Moreart",
    "Чем прежде - Полка", "SMS (Slowed) - UncleFlexxx", "Намёк на нас - MOT",
    "Народ задыхался от боли - KAMILL'FO", "Вот уж вечер. Роса ft. С. Есенин - 10AGE",
    "Mafia Style - TRAP MAFIA HOUSE", "Базовый минимум - Sahi MIA ROYKA",
    "Витя АК - Бурановские бабушки", "Фраера - АлСми", "Молча - GUF, VEIGEL",
    "Наследство - ICEGERGERT, SKY RAE", "Чегери - SHAMO", "Еще один вечер - Ramil'",
    "Силуэт из к/ф «Алиса в Стране Чу...» - Ваня Дмитриенко, Аня Пересильд",
    "Шутка - Akmal', Григорий Лепс", "Внутренний голос - Jeny Vesna", "Карта битая - Kiliana",
    "Худи - Джиган, ARTIK & ASTI, NILETTO", "I Got Love - Miyagi & Эндшпиль feat. Рем Дигга"
]

# ========== КНОПКИ ==========
def main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Найти музыку", "🆕 Новинки")
    if is_admin:
        markup.add("🔗 Рефералка")
    markup.add("❓ Помощь")
    return markup

def ref_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📝 Создать ссылку", callback_data="create_ref"),
        types.InlineKeyboardButton("📊 Мои ссылки", callback_data="my_refs")
    )
    return markup

# ========== ПОИСК НА YOUTUBE ==========
def search_youtube(query, max_results=10):
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch',
        'extract_flat': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{max_results}:{query} audio"
            info = ydl.extract_info(search_query, download=False)
            tracks = []
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        title = entry.get('title', 'Unknown')
                        duration = entry.get('duration', 0)
                        if duration and 60 <= duration <= 360:
                            tracks.append({
                                'title': title,
                                'url': entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}",
                                'duration': duration
                            })
            return tracks
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

# ========== СКАЧИВАНИЕ (исправленное) ==========
def download_audio(url, title):
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
        'outtmpl': f'/tmp/{safe_title}.%(ext)s',
        'quiet': True,
        'ignoreerrors': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("Нет данных")
            
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base = filename.rsplit('.', 1)[0]
                for ext in ['.mp3', '.m4a', '.webm']:
                    if os.path.exists(base + ext):
                        return base + ext
            return filename
    except Exception as e:
        print(f"Ошибка: {e}")
        opts['format'] = 'bestaudio/best'
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

def format_time(seconds):
    if not seconds:
        return "00:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"

# ========== ПОКАЗ ТРЕКОВ ==========
user_tracks = {}

def show_tracks(chat_id, tracks, title, page=0, per_page=10):
    if not tracks:
        bot.send_message(chat_id, "❌ Ничего не найдено.")
        return
    
    total_pages = (len(tracks) + per_page - 1) // per_page
    start = page * per_page
    end = min(start + per_page, len(tracks))
    page_tracks = tracks[start:end]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, t in enumerate(page_tracks):
        idx = start + i
        duration = format_time(t.get('duration'))
        markup.add(types.InlineKeyboardButton(f"🎵 {t['title'][:45]} [{duration}]", callback_data=f"play_{idx}"))
    
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
        if page < total_pages - 1:
            nav.append(types.InlineKeyboardButton("➡️ Далее", callback_data=f"page_{page+1}"))
        if nav:
            markup.add(*nav)
    
    user_tracks[chat_id] = tracks
    bot.send_message(chat_id, f"🎵 *{title}* (стр. {page+1}/{total_pages})", reply_markup=markup, parse_mode='Markdown')

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    args = message.text.split()
    referrer = None
    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            referrer = int(args[1].split('_')[1])
        except:
            pass
    
    add_user(user_id, username, referrer)
    
    is_admin = (user_id == ADMIN_ID)
    bot.send_message(message.chat.id, "🎵 *Музыкальный бот готов!*\n\nИспользуй кнопки внизу.", reply_markup=main_menu(is_admin), parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "🎵 Найти музыку")
def search_cmd(message):
    bot.send_message(message.chat.id, "🔍 *Напиши название песни или исполнителя*", parse_mode='Markdown')
    bot.register_next_step_handler(message, do_search)

def do_search(message):
    msg = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    tracks = search_youtube(message.text, max_results=50)
    
    if tracks:
        bot.delete_message(message.chat.id, msg.message_id)
        show_tracks(message.chat.id, tracks, f"Результаты: {message.text}")
    else:
        bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "🆕 Новинки")
def new_cmd(message):
    tracks = [{'title': t, 'url': f"https://youtube.com/results?search_query={t.replace(' ', '+')}", 'duration': 180} for t in NEW_TRACKS]
    show_tracks(message.chat.id, tracks, "🆕 Новинки")

@bot.message_handler(func=lambda msg: msg.text == "🔗 Рефералка")
def ref_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только для создателя.")
        return
    
    bot.send_message(message.chat.id, "🔗 *Реферальная панель*", reply_markup=ref_menu(), parse_mode='Markdown')

# ========== РЕФЕРАЛЬНЫЕ КНОПКИ ==========
@bot.callback_query_handler(func=lambda call: call.data == "create_ref")
def create_ref(call):
    bot.send_message(call.message.chat.id, "📝 *Введи Telegram ID пользователя*\n\nНапример: `5298604296`", parse_mode='Markdown')
    bot.register_next_step_handler(call.message, process_create_ref)

def process_create_ref(message):
    try:
        user_id = int(message.text.strip())
        code = f"ref_{user_id}_{int(time.time())}"
        add_ref_link(code, user_id, ADMIN_ID)
        
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={code}"
        
        text = f"""✅ *Реферальная ссылка создана!*

👤 Для пользователя: `{user_id}`
🔗 Ссылка: `{ref_link}`

📊 *Отслеживание:*
Переходы по этой ссылке будут отображаться в разделе "Мои ссылки"."""
        
        bot.send_message(message.chat.id, text, reply_markup=main_menu(True), parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID. Попробуй ещё раз.", reply_markup=main_menu(True))

@bot.callback_query_handler(func=lambda call: call.data == "my_refs")
def my_refs(call):
    links = get_ref_links(ADMIN_ID)
    
    if not links:
        bot.send_message(call.message.chat.id, "📭 *У тебя пока нет созданных ссылок*", reply_markup=ref_menu(), parse_mode='Markdown')
        return
    
    text = "🔗 *Твои реферальные ссылки:*\n\n"
    for link in links[:10]:  # показываем последние 10
        text += f"📌 `ref_{link[3]}` — переходов: {link[4]}\n"
    
    bot.send_message(call.message.chat.id, text, reply_markup=ref_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "❓ Помощь")
def help_cmd(message):
    is_admin = (message.from_user.id == ADMIN_ID)
    help_text = """🎵 *Музыкальный бот*

🎵 *Найти музыку* — найди любую песню
🆕 *Новинки* — свежие треки (до 6 минут)
❓ *Помощь* — это сообщение

*Как пользоваться:*
1. Нажми "Найти музыку" и введи название
2. Выбери трек из списка
3. Бот скачает и отправит MP3

*По вопросам:* @avgustc"""
    
    if is_admin:
        help_text += "\n\n🔗 *Рефералка* — создавай ссылки и отслеживай переходы"
    
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu(is_admin), parse_mode='Markdown')

# ========== НАВИГАЦИЯ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_page(call):
    page = int(call.data.split('_')[1])
    tracks = user_tracks.get(call.message.chat.id, [])
    if not tracks:
        bot.answer_callback_query(call.id, "❌ Результаты поиска устарели")
        return
    
    title = call.message.text.split('*')[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_tracks(call.message.chat.id, tracks, title, page)

# ========== СКАЧИВАНИЕ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def play_track(call):
    idx = int(call.data.split('_')[1])
    tracks = user_tracks.get(call.message.chat.id, [])
    if idx >= len(tracks):
        bot.answer_callback_query(call.id, "❌ Трек не найден")
        return
    
    track = tracks[idx]
    bot.answer_callback_query(call.id, "⏳ Скачиваю...")
    msg = bot.send_message(call.message.chat.id, f"🎵 *{track['title']}*\n⏳ Скачивание...", parse_mode='Markdown')
    
    try:
        if 'youtube.com' not in track['url']:
            search_result = search_youtube(track['title'], max_results=1)
            if search_result:
                track = search_result[0]
            else:
                raise Exception("Трек не найден на YouTube")
        
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

if __name__ == '__main__':
    print("🎵 Музыкальный бот запущен!")
    bot.polling(none_stop=True)
