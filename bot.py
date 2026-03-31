import telebot
from telebot import types
import yt_dlp
import os
import re
import time
import sqlite3
from datetime import datetime

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
ADMIN_ID = 5298604296
BOT_USERNAME = 'reservettbot'
bot = telebot.TeleBot(BOT_TOKEN)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_seen TEXT, referrer_id INTEGER, ref_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ref_links (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, user_id INTEGER, created_by INTEGER, created_at TEXT, clicks INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen, referrer_id) VALUES (?, ?, ?, ?)", (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), referrer_id))
    if referrer_id and referrer_id != user_id:
        c.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?", (referrer_id,))
    conn.commit()
    conn.close()

def add_ref_link(code, user_id, created_by):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO ref_links (code, user_id, created_by, created_at) VALUES (?, ?, ?, ?)", (code, user_id, created_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_ref_links(created_by):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("SELECT id, code, user_id, created_at, clicks FROM ref_links WHERE created_by = ? ORDER BY id DESC", (created_by,))
    return c.fetchall()

def get_ref_link_by_code(code):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("SELECT id, code, user_id, created_at, clicks FROM ref_links WHERE code = ?", (code,))
    return c.fetchone()

def click_ref_link(code):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("UPDATE ref_links SET clicks = clicks + 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def delete_ref_link(code):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM ref_links WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def get_ref_stats(user_id):
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("SELECT ref_count FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0

def get_total_users():
    conn = sqlite3.connect('music_bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0

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
    "Mafia Style - TRAP MAFIA HOUSE", "Базовый минимум - Sahi MIA ROYKA"
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
    markup.add(types.InlineKeyboardButton("📝 Создать ссылку", callback_data="create_ref"))
    markup.add(types.InlineKeyboardButton("📊 Мои ссылки", callback_data="my_refs"))
    return markup

# ========== ПОИСК И СКАЧИВАНИЕ ==========
def search_youtube(query):
    ydl_opts = {'quiet': True, 'default_search': 'ytsearch5', 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            tracks = []
            if info and 'entries' in info:
                for e in info['entries']:
                    if e:
                        dur = e.get('duration', 0)
                        if dur and 60 <= dur <= 360:
                            tracks.append({
                                'title': e.get('title', 'Unknown'),
                                'url': e.get('url') or f"https://youtube.com/watch?v={e.get('id')}",
                                'duration': dur
                            })
            return tracks
    except:
        return []

def download_audio(url, title):
    safe = re.sub(r'[^\w\s-]', '', title)[:50]
    opts = {'format': 'bestaudio/best', 'outtmpl': f'/tmp/{safe}.%(ext)s', 'quiet': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

def format_time(sec):
    if not sec: return "00:00"
    return f"{int(sec)//60}:{int(sec)%60:02d}"

user_tracks = {}

def show_tracks(chat_id, tracks, title, page=0):
    if not tracks:
        bot.send_message(chat_id, "❌ Ничего не найдено.")
        return
    per_page = 10
    total = (len(tracks) + per_page - 1) // per_page
    start = page * per_page
    end = min(start + per_page, len(tracks))
    page_tracks = tracks[start:end]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, t in enumerate(page_tracks):
        idx = start + i
        markup.add(types.InlineKeyboardButton(f"🎵 {t['title'][:45]} [{format_time(t['duration'])}]", callback_data=f"play_{idx}"))
    
    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{title}_{page-1}"))
    if page < total - 1: nav.append(types.InlineKeyboardButton("➡️ Далее", callback_data=f"page_{title}_{page+1}"))
    if nav: markup.add(*nav)
    
    user_tracks[chat_id] = tracks
    bot.send_message(chat_id, f"🎵 *{title}* (стр. {page+1}/{total})", reply_markup=markup, parse_mode='Markdown')

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    uname = m.from_user.username or "unknown"
    args = m.text.split()
    ref = None
    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            link = get_ref_link_by_code(args[1])
            if link:
                click_ref_link(args[1])
                ref = link[2]
        except: pass
    add_user(uid, uname, ref)
    bot.send_message(m.chat.id, "🎵 *Музыкальный бот готов!*", reply_markup=main_menu(uid == ADMIN_ID), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🎵 Найти музыку")
def search_cmd(m):
    bot.send_message(m.chat.id, "🔍 *Напиши название песни*", parse_mode='Markdown')
    bot.register_next_step_handler(m, do_search)

def do_search(m):
    msg = bot.send_message(m.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    tracks = search_youtube(m.text)
    if tracks:
        bot.delete_message(m.chat.id, msg.message_id)
        show_tracks(m.chat.id, tracks, f"Результаты: {m.text}")
    else:
        bot.edit_message_text("❌ Ничего не найдено.", m.chat.id, msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🆕 Новинки")
def new_cmd(m):
    tracks = [{'title': t, 'url': f"https://youtube.com/results?search_query={t.replace(' ', '+')}", 'duration': 180} for t in NEW_TRACKS]
    show_tracks(m.chat.id, tracks, "🆕 Новинки")

@bot.message_handler(func=lambda m: m.text == "🔗 Рефералка")
def ref_cmd(m):
    if m.from_user.id != ADMIN_ID:
        bot.send_message(m.chat.id, "❌ Только для создателя.")
        return
    bot.send_message(m.chat.id, "🔗 *Реферальная панель*", reply_markup=ref_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "create_ref")
def create_ref(call):
    bot.send_message(call.message.chat.id, "📝 *Введи Telegram ID*", parse_mode='Markdown')
    bot.register_next_step_handler(call.message, process_create)

def process_create(m):
    try:
        uid = int(m.text.strip())
        code = f"ref_{uid}_{int(time.time())}"
        add_ref_link(code, uid, ADMIN_ID)
        ref_link = f"https://t.me/{bot.get_me().username}?start={code}"
        bot.send_message(m.chat.id, f"✅ Ссылка: `{ref_link}`\n👤 Для: `{uid}`", parse_mode='Markdown')
    except:
        bot.send_message(m.chat.id, "❌ Неверный ID.")

@bot.callback_query_handler(func=lambda call: call.data == "my_refs")
def my_refs(call):
    links = get_ref_links(ADMIN_ID)
    if not links:
        bot.send_message(call.message.chat.id, "📭 *Нет ссылок*", reply_markup=ref_menu(), parse_mode='Markdown')
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for link in links:
        code = link[1]
        suffix = code.split('_')[2] if '_' in code else code
        markup.add(types.InlineKeyboardButton(f"📊 {suffix} — {link[4]} переходов", callback_data=f"link_{code}"))
    bot.send_message(call.message.chat.id, "🔗 *Твои ссылки:*", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('link_'))
def link_stats(call):
    code = call.data[5:]
    link = get_ref_link_by_code(code)
    if not link:
        bot.answer_callback_query(call.id, "❌ Не найдена")
        return
    ref_link = f"https://t.me/{bot.get_me().username}?start={code}"
    suffix = code.split('_')[2] if '_' in code else code
    text = f"📊 *Статистика*\n🔗 `{ref_link}`\n👨‍💻 Переходов: {link[4]}\n🗑 `/dellink_{suffix}`"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{code}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="my_refs"))
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_link(call):
    code = call.data[7:]
    delete_ref_link(code)
    bot.answer_callback_query(call.id, "✅ Удалено!")
    bot.edit_message_text("🗑 Удалено", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_page(call):
    _, title, page = call.data.split('_')
    page = int(page)
    tracks = user_tracks.get(call.message.chat.id)
    if not tracks:
        bot.answer_callback_query(call.id, "❌ Устарело")
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_tracks(call.message.chat.id, tracks, title, page)

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
            bot.send_audio(call.message.chat.id, f, title=track['title'], caption=f"🎵 *{track['title']}*\n\n📥 Скачано с @{BOT_USERNAME}")
        os.remove(file)
        bot.delete_message(call.message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {str(e)[:100]}", call.message.chat.id, msg.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_cmd(m):
    is_admin = m.from_user.id == ADMIN_ID
    text = "🎵 *Музыкальный бот*\n\n🎵 Найти музыку\n🆕 Новинки"
    if is_admin:
        text += "\n\n🔗 Рефералка — создавай ссылки\n🗑 `/dellink_название`"
    text += "\n\n@avgustc"
    bot.send_message(m.chat.id, text, reply_markup=main_menu(is_admin), parse_mode='Markdown')

if __name__ == '__main__':
    print("🎵 Бот запущен!")
    bot.polling(none_stop=True)
