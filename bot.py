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

def get_user_info(user_id):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("SELECT username, first_seen, referrer_id, ref_count FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

init_db()

# ========== ПОПУЛЯРНЫЕ ТРЕКИ ==========
POPULAR_TRACKS = [
    "SMS - UncleFlexxx", "Тону - HOLLYFLAME", "КУКЛА Remix 2026 - Дискотека Авария, VONAMOUR",
    "Плакала надежда - Jakone, Kiliana, Любовь Успенская", "NOBODY - Aarne, Toxi$, Big Baby Tape",
    "Гаснет свет - Nasty Babe", "КУПЕР - SQWOZ BAB", "БАНК - ICEGERGERT, Zivert",
    "Цыганка нагадала - Artem Smile", "Феникс - BEARWOLF", "Жиганская - Jakone, Kiliana",
    "Сыпь, гармоника! - СДП", "G-Woman - ICEGERGERT", "Дэнс - 9 Грамм",
    "Сердце - Альберт Назранов", "На мурмулях - Это Радио", "Tom Ford - Moreart",
    "Чем прежде - Полка", "SMS (Slowed) - UncleFlexxx", "Намёк на нас - MOT",
    "Народ задыхался от боли - KAMILL'FO", "Вот уж вечер. Роса ft. С. Есенин - 10AGE",
    "Mafia Style - TRAP MAFIA HOUSE", "Базовый минимум - Sahi MIA ROYKA"
]

# ========== КНОПКИ ==========
def main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Поиск музыки", "🔥 Популярное")
    if is_admin:
        markup.add("🔗 Моя рефка", "👥 Рефка для друга")
        markup.add("📊 Реф статистика")
    markup.add("❓ Помощь")
    return markup

# ========== ПОИСК НА YOUTUBE ==========
def search_youtube(query):
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch',
        'extract_flat': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch5:{query} audio"
            info = ydl.extract_info(search_query, download=False)
            tracks = []
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        title = entry.get('title', 'Unknown')
                        duration = entry.get('duration', 0)
                        if duration and 60 <= duration <= 600:
                            tracks.append({
                                'title': title,
                                'url': entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}",
                                'duration': duration
                            })
            return tracks
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

# ========== СКАЧИВАНИЕ ==========
def download_audio(url, title):
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
        'outtmpl': f'/tmp/{safe_title}.%(ext)s',
        'quiet': True,
        'ignoreerrors': True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base = filename.rsplit('.', 1)[0]
                for ext in ['.mp3', '.m4a', '.webm']:
                    if os.path.exists(base + ext):
                        return base + ext
            return filename
    except Exception as e:
        raise Exception(f"Ошибка: {e}")

def format_time(seconds):
    if not seconds:
        return "00:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"

# ========== ПОКАЗ ТРЕКОВ ==========
user_tracks = {}

def show_tracks(chat_id, tracks, title, page=0, per_page=5):
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

@bot.message_handler(func=lambda msg: msg.text == "🎵 Поиск музыки")
def search_cmd(message):
    bot.send_message(message.chat.id, "🔍 *Напиши название песни или исполнителя*", parse_mode='Markdown')
    bot.register_next_step_handler(message, do_search)

def do_search(message):
    msg = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    tracks = search_youtube(message.text)
    
    if tracks:
        bot.delete_message(message.chat.id, msg.message_id)
        show_tracks(message.chat.id, tracks, f"Результаты: {message.text}")
    else:
        bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "🔥 Популярное")
def popular_cmd(message):
    tracks = [{'title': t, 'url': f"https://youtube.com/results?search_query={t.replace(' ', '+')}", 'duration': 180} for t in POPULAR_TRACKS]
    show_tracks(message.chat.id, tracks, "🔥 Популярное")

@bot.message_handler(func=lambda msg: msg.text == "🔗 Моя рефка")
def my_ref_cmd(message):
    user_id = message.from_user.id
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    ref_count = get_ref_stats(user_id)
    
    text = f"""🔗 *Твоя реферальная ссылка*

`{ref_link}`

📊 *Твоя статистика:*
• Приглашено: {ref_count}
• Всего пользователей: {get_total_users()}"""
    
    bot.send_message(message.chat.id, text, reply_markup=main_menu(user_id == ADMIN_ID), parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "👥 Рефка для друга")
def create_ref_for_friend(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только для создателя.")
        return
    
    bot.send_message(message.chat.id, "📝 *Введи Telegram ID пользователя*\n\nНапример: `5298604296`", parse_mode='Markdown')
    bot.register_next_step_handler(message, process_friend_ref)

def process_friend_ref(message):
    try:
        friend_id = int(message.text.strip())
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{friend_id}"
        ref_count = get_ref_stats(friend_id)
        
        # Получаем информацию о пользователе
        user_info = get_user_info(friend_id)
        username = user_info[0] if user_info else "неизвестно"
        first_seen = user_info[1] if user_info else "неизвестно"
        
        text = f"""🔗 *Реферальная ссылка для пользователя*

👤 ID: `{friend_id}`
👤 Username: @{username}

🔗 Ссылка: `{ref_link}`

📊 *Его статистика:*
• Приглашено: {ref_count}
• Всего пользователей: {get_total_users()}
• Впервые в боте: {first_seen}"""
        
        bot.send_message(message.chat.id, text, reply_markup=main_menu(True), parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID. Попробуй ещё раз.", reply_markup=main_menu(True))

@bot.message_handler(func=lambda msg: msg.text == "📊 Реф статистика")
def ref_stats_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только для создателя.")
        return
    
    bot.send_message(message.chat.id, "📝 *Введи Telegram ID пользователя*\n\nНапример: `5298604296`", parse_mode='Markdown')
    bot.register_next_step_handler(message, show_user_stats)

def show_user_stats(message):
    try:
        user_id = int(message.text.strip())
        ref_count = get_ref_stats(user_id)
        user_info = get_user_info(user_id)
        
        username = user_info[0] if user_info else "неизвестно"
        first_seen = user_info[1] if user_info else "неизвестно"
        referrer_id = user_info[2] if user_info else None
        invited = user_info[3] if user_info else 0
        
        text = f"""📊 *Статистика пользователя*

👤 ID: `{user_id}`
👤 Username: @{username}

📈 *Реферальная статистика:*
• Приглашено: {invited}
• Пришёл по ссылке от: {referrer_id if referrer_id else 'сам'}

📅 *Активность:*
• Впервые в боте: {first_seen}
• Всего пользователей: {get_total_users()}"""
        
        bot.send_message(message.chat.id, text, reply_markup=main_menu(True), parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID. Попробуй ещё раз.", reply_markup=main_menu(True))

@bot.message_handler(func=lambda msg: msg.text == "❓ Помощь")
def help_cmd(message):
    is_admin = (message.from_user.id == ADMIN_ID)
    help_text = """🎵 *Музыкальный бот*

*Команды:*
🎵 Поиск музыки — найди любую песню
🔥 Популярное — топ треки"""
    
    if is_admin:
        help_text += """
        
🔗 Моя рефка — твоя реферальная ссылка
👥 Рефка для друга — создать ссылку для друга
📊 Реф статистика — статистика пользователя"""
    
    help_text += """

❓ Помощь — это сообщение

@avgustc"""
    
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu(is_admin), parse_mode='Markdown')

# ========== НАВИГАЦИЯ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_page(call):
    page = int(call.data.split('_')[1])
    tracks = user_tracks.get(call.message.chat.id, [])
    if not tracks:
        bot.answer_callback_query(call.id, "❌ Результаты поиска устарели")
        return
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_tracks(call.message.chat.id, tracks, call.message.text.split('*')[1].split('*')[0], page)

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
            search_result = search_youtube(track['title'])
            if search_result:
                track = search_result[0]
            else:
                raise Exception("Трек не найден")
        
        file = download_audio(track['url'], track['title'])
        with open(file, 'rb') as f:
            bot.send_audio(call.message.chat.id, f, title=track['title'])
        os.remove(file)
        bot.delete_message(call.message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {str(e)[:100]}", call.message.chat.id, msg.message_id, parse_mode='Markdown')

if __name__ == '__main__':
    print("🎵 Музыкальный бот запущен!")
    bot.polling(none_stop=True)
