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
BOT_TOKEN = '8347775737:AAFSFwXxse-7c3SsOu4JSTN7jSfdYh4vJa4'
ADMIN_ID = 405071693  # 👈 ТВОЙ TELEGRAM ID
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
    if referrer_id:
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

init_db()

# ========== ТВОИ ТРЕКИ ==========
TOP_TRACKS = [
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

NEW_TRACKS = [
    "Малиновое небо 2026 - Флит", "Мимолетно - лучиадежды", "Обман - Remixoviy, Batrai",
    "Больше, чем ближе - NAVAI", "Как к себе домой LA LA LA LA - MOT",
    "say something - Royel Otis", "Лепесточек - Честный", "ВАТ ИЗ ЛАВ - Junior",
    "Ворона - Кэнни feat. MC Дымка", "Пропадает - 10AGE, Анет Сай",
    "днями и ночами - BUSHIDO ZHO, Scally Milano, Полка", "Ла ла лэй - 9 Грамм",
    "КУПЕР - SQWOZ BAB", "Тону - HOLLYFLAME", "SMS - UncleFlexxx"
]

# ========== КНОПКИ ==========
def main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if is_admin:
        markup.add("🎵 Поиск музыки", "🆕 Новинки")
        markup.add("🔥 Топ 100", "🔗 Рефералка")
        markup.add("❓ Помощь")
    else:
        markup.add("🎵 Поиск музыки", "🆕 Новинки")
        markup.add("🔥 Топ 100", "❓ Помощь")
    return markup

# ========== ПОИСК И СКАЧИВАНИЕ ==========
def search_youtube(query):
    ydl_opts = {'quiet': True, 'default_search': 'ytsearch5', 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        tracks = []
        if 'entries' in info:
            for entry in info['entries'][:5]:
                if entry:
                    tracks.append({
                        'title': entry.get('title', 'Unknown'),
                        'url': entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}",
                        'duration': entry.get('duration', 0)
                    })
        return tracks

def download_audio(url, title):
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
        'outtmpl': f'/tmp/{safe_title}.%(ext)s',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

def format_time(seconds):
    if not seconds:
        return "00:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"

# ========== ОТОБРАЖЕНИЕ ТРЕКОВ ==========
user_tracks = {}

def show_tracks(chat_id, tracks, title):
    if not tracks:
        bot.send_message(chat_id, "❌ Ничего не найдено.")
        return
    user_tracks[chat_id] = tracks
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, t in enumerate(tracks):
        duration = format_time(t.get('duration'))
        markup.add(types.InlineKeyboardButton(f"🎵 {t['title'][:45]} [{duration}]", callback_data=f"play_{i}"))
    bot.send_message(chat_id, f"🎵 *{title}*", reply_markup=markup, parse_mode='Markdown')

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    args = message.text.split()
    referrer = None
    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            referrer = int(args[1].split('_')[1])
        except:
            pass
    
    add_user(user_id, username, referrer)
    
    is_admin = (user_id == ADMIN_ID)
    bot.send_message(message.chat.id, "🎵 *Музыкальный бот готов!*", reply_markup=main_menu(is_admin), parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "🎵 Поиск музыки")
def search_cmd(message):
    bot.send_message(message.chat.id, "🔍 *Напиши название песни*", parse_mode='Markdown')
    bot.register_next_step_handler(message, do_search)

def do_search(message):
    msg = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    tracks = search_youtube(message.text)
    if tracks:
        bot.delete_message(message.chat.id, msg.message_id)
        show_tracks(message.chat.id, tracks, f"Результаты: {message.text}")
    else:
        bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "🆕 Новинки")
def new_cmd(message):
    tracks = [{'title': t, 'url': f"https://youtube.com/results?search_query={t.replace(' ', '+')}", 'duration': 180} for t in NEW_TRACKS]
    show_tracks(message.chat.id, tracks, "🆕 Новинки")

@bot.message_handler(func=lambda msg: msg.text == "🔥 Топ 100")
def top_cmd(message):
    tracks = [{'title': t, 'url': f"https://youtube.com/results?search_query={t.replace(' ', '+')}", 'duration': 180} for t in TOP_TRACKS]
    show_tracks(message.chat.id, tracks, "🔥 Топ 100")

@bot.message_handler(func=lambda msg: msg.text == "🔗 Рефералка")
def ref_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только для создателя.")
        return
    
    ref_count = get_ref_stats(ADMIN_ID)
    total_users = get_total_users()
    ref_link = f"https://t.me/твой_бот?start=ref_{ADMIN_ID}"
    
    text = f"""🔗 *Реферальная ссылка*

`{ref_link}`

📊 *Статистика:*
• Приглашено: {ref_count}
• Всего пользователей: {total_users}"""
    
    bot.send_message(message.chat.id, text, reply_markup=main_menu(True), parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "❓ Помощь")
def help_cmd(message):
    help_text = """🎵 *Музыкальный бот*

🔍 Поиск — найди любую песню
🆕 Новинки — свежие треки
🔥 Топ 100 — популярное

@avgustc"""
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu(message.from_user.id == ADMIN_ID), parse_mode='Markdown')

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
        file = download_audio(track['url'], track['title'])
        with open(file, 'rb') as f:
            bot.send_audio(call.message.chat.id, f, title=track['title'])
        os.remove(file)
        bot.delete_message(call.message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, msg.message_id, parse_mode='Markdown')

if __name__ == '__main__':
    print("🎵 Музыкальный бот запущен!")
    bot.polling(none_stop=True)
