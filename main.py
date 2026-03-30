import telebot
from telebot import types
import yt_dlp
import os
import re
import random
import subprocess

# Обновляем yt-dlp
try:
    subprocess.run(['pip', 'install', '--upgrade', 'yt-dlp'], capture_output=True)
except:
    pass

TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
CHANNEL_ID = '-1001888094511'
CHANNEL_URL = 'https://t.me/lyubimkatt'

bot = telebot.TeleBot(TG_TOKEN)
user_tracks = {}
popular_cache = []

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Поиск музыки")
    markup.add("🔥 Популярное", "🎲 Рандом")
    return markup

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def is_good_track(title):
    """Умеренная фильтрация: исключаем явные плейлисты и сборники"""
    title_lower = title.lower()
    
    # Только явные плохие слова
    bad_words = [
        'плейлист', 'playlist', 'mix', 'сборник', 'megamix', 'попурри',
        'live', 'концерт', 'remix', 'cover', 'кавер', 'instrumental', 'минус',
        'slowed', 'reverb', 'speed up', 'nightcore', '8d'
    ]
    
    for word in bad_words:
        if word in title_lower:
            return False
    
    # Длительность 1.5 - 8 минут
    return True

def search_youtube(query, max_results=20):
    """Поиск треков"""
    ydl_opts = {'quiet': True, 'default_search': 'ytsearch', 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_query = f"ytsearch{max_results}:{query}"
        info = ydl.extract_info(search_query, download=False)
        tracks = []
        if 'entries' in info:
            for entry in info['entries']:
                if entry:
                    title = entry.get('title', 'Unknown')
                    duration = entry.get('duration', 0)
                    # Фильтр: длительность 1.5-8 минут, не плейлист
                    if 90 <= duration <= 480 and is_good_track(title):
                        tracks.append({
                            'title': title,
                            'url': entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}",
                            'duration': duration
                        })
                        if len(tracks) >= 10:
                            break
        return tracks

def get_popular():
    """Получает популярные треки"""
    global popular_cache
    if popular_cache:
        return popular_cache
    popular_cache = search_youtube("популярные песни")
    return popular_cache

def download_audio(url, title):
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
        'outtmpl': f'/tmp/{safe_title}.%(ext)s',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename

def show_tracks(chat_id, tracks, title):
    if not tracks:
        bot.send_message(chat_id, "❌ Ничего не найдено. Попробуй другой запрос.")
        return
    user_tracks[chat_id] = tracks
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, track in enumerate(tracks[:10]):
        duration = track.get('duration', 0)
        minutes = duration // 60
        seconds = duration % 60
        display_title = track['title'][:50]
        button_text = f"🎵 {display_title} [{minutes}:{seconds:02d}]"
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=f"play_{i}"))
    bot.send_message(chat_id, f"🎵 *{title}*", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub"))
        bot.send_message(message.chat.id, "⚠️ *Доступ закрыт!*\n\nПодпишись на канал.", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "🎵 *Муз-бот готов!*", reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == "🎵 Поиск музыки")
def search_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    bot.send_message(message.chat.id, "🔍 *Напиши название песни или исполнителя*", parse_mode='Markdown')
    bot.register_next_step_handler(message, process_search)

def process_search(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    wait = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    tracks = search_youtube(message.text)
    if tracks:
        bot.delete_message(message.chat.id, wait.message_id)
        show_tracks(message.chat.id, tracks, f"Результаты: {message.text}")
    else:
        bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)

@bot.message_handler(func=lambda msg: msg.text == "🔥 Популярное")
def popular_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    wait = bot.send_message(message.chat.id, "🔎 *Загружаю популярное...*", parse_mode='Markdown')
    tracks = get_popular()
    if tracks:
        bot.delete_message(message.chat.id, wait.message_id)
        show_tracks(message.chat.id, tracks, "🔥 Популярное")
    else:
        bot.edit_message_text("❌ Не удалось загрузить популярное.", message.chat.id, wait.message_id)

@bot.message_handler(func=lambda msg: msg.text == "🎲 Рандом")
def random_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    tracks = get_popular()
    if not tracks:
        bot.send_message(message.chat.id, "❌ Не удалось загрузить популярное.")
        return
    random_track = random.choice(tracks)
    bot.send_message(message.chat.id, f"🎲 *Случайный трек:*\n{random_track['title']}\n⏳ Скачиваю...", parse_mode='Markdown')
    try:
        file_path = download_audio(random_track['url'], random_track['title'])
        with open(file_path, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, title=random_track['title'][:100])
        os.remove(file_path)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def play_track(call):
    idx = int(call.data.split('_')[1])
    tracks = user_tracks.get(call.message.chat.id, [])
    if idx >= len(tracks):
        bot.answer_callback_query(call.id, "❌ Трек не найден")
        return
    track = tracks[idx]
    bot.answer_callback_query(call.id, f"⏳ Скачиваю...")
    status_msg = bot.send_message(call.message.chat.id, f"🎵 *{track['title']}*\n⏳ Скачивание...", parse_mode='Markdown')
    try:
        file_path = download_audio(track['url'], track['title'])
        with open(file_path, 'rb') as audio:
            bot.send_audio(call.message.chat.id, audio, title=track['title'][:100])
        os.remove(file_path)
        bot.delete_message(call.message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_callback(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Подписка подтверждена!")
        bot.edit_message_text("🎉 Спасибо! Теперь ты можешь слушать музыку.", call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "🎵 *Муз-бот готов!*", reply_markup=main_menu(), parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписаны!", show_alert=True)

if __name__ == '__main__':
    print("🎵 Музыкальный бот запущен!")
    bot.polling(none_stop=True)
