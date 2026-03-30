import telebot
from telebot import types
import yt_dlp
import os
import random

# ========== НАСТРОЙКИ ==========
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
CHANNEL_ID = '-1001888094511'
CHANNEL_URL = 'https://t.me/lyubimkatt'

bot = telebot.TeleBot(TG_TOKEN)

# ========== НАСТРОЙКИ ПОИСКА ==========
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch10',
}

user_results = {}

# ========== ПРОВЕРКА ПОДПИСКИ ==========
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# ========== КНОПКИ ГЛАВНОГО МЕНЮ ==========
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Поиск музыки")
    markup.add("🆕 Новинки", "🔥 Топ 100")
    return markup

# ========== СКАЧИВАНИЕ АУДИО ==========
def download_audio(url, title):
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'/tmp/{title}.%(ext)s',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename.rsplit('.', 1)[0] + '.mp3'

# ========== НОВИНКИ (пример) ==========
def get_new():
    return [
        "Miyagi - I Got Love",
        "INSTASAMKA - За деньги да",
        "Zivert - Топай",
        "Jony - Давай сбежим",
        "Morgenshtern - Почему?",
        "The Limba - Забери"
    ]

# ========== ТОП 100 (пример) ==========
def get_top():
    return [
        "Imagine Dragons - Believer",
        "Billie Eilish - Birds of a Feather",
        "The Weeknd - Blinding Lights",
        "Glass Animals - Heat Waves",
        "Rauf & Faik - Я люблю тебя"
    ]

# ========== ПОИСК МУЗЫКИ ==========
def search_music(query, chat_id):
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"{query} audio", download=False)
            tracks = [e for e in info['entries'] if e]
        
        if not tracks:
            return None
        
        user_results[chat_id] = tracks
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, track in enumerate(tracks[:5]):
            title = track.get('title', 'Track')[:45]
            markup.add(types.InlineKeyboardButton(text=f"🎵 {title}", callback_data=f"mus_{i}"))
        return markup, tracks[0]['title']
    except:
        return None

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub"))
        bot.send_message(
            message.chat.id,
            "⚠️ *Доступ к музыкальному боту закрыт!*\n\nПодпишись на наш канал, чтобы искать и скачивать музыку бесплатно!",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.send_message(
            message.chat.id,
            "🎵 *Муз-бот готов!*\n\nИспользуй кнопки внизу:",
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )

# ========== ПРОВЕРКА ПОДПИСКИ ПОСЛЕ КНОПКИ ==========
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_callback(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Подписка подтверждена!")
        bot.edit_message_text(
            "🎉 Спасибо за подписку!\n\nТеперь ты можешь искать музыку через кнопки внизу.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.send_message(
            call.message.chat.id,
            "🎵 *Муз-бот готов!*",
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "❌ Вы всё еще не подписаны!", show_alert=True)

# ========== КНОПКА "ПОИСК МУЗЫКИ" ==========
@bot.message_handler(func=lambda msg: msg.text == "🎵 Поиск музыки")
def search_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал! Используй /start")
        return
    bot.send_message(message.chat.id, "🔍 *Напиши название песни или исполнителя*", parse_mode='Markdown')
    bot.register_next_step_handler(message, process_search)

def process_search(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал! Используй /start")
        return
    
    wait = bot.send_message(message.chat.id, "🔎 *Ищу треки...*", parse_mode='Markdown')
    result = search_music(message.text, message.chat.id)
    
    if result:
        markup, title = result
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(
            message.chat.id,
            f"🎵 *Результаты для:* {message.text}",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)

# ========== КНОПКА "НОВИНКИ" ==========
@bot.message_handler(func=lambda msg: msg.text == "🆕 Новинки")
def new_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал! Используй /start")
        return
    
    new_tracks = get_new()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for track in new_tracks[:5]:
        markup.add(types.InlineKeyboardButton(text=f"🎵 {track[:40]}", callback_data=f"search_{track}"))
    
    bot.send_message(
        message.chat.id,
        "🆕 *Новинки недели:*\n\nНажми на трек, чтобы найти и скачать.",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ========== КНОПКА "ТОП 100" ==========
@bot.message_handler(func=lambda msg: msg.text == "🔥 Топ 100")
def top_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал! Используй /start")
        return
    
    top_tracks = get_top()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for track in top_tracks[:5]:
        markup.add(types.InlineKeyboardButton(text=f"🎵 {track[:40]}", callback_data=f"search_{track}"))
    
    bot.send_message(
        message.chat.id,
        "🔥 *Топ 100 недели:*\n\nНажми на трек, чтобы найти и скачать.",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ========== ОБРАБОТКА ВЫБОРА ТРЕКА ИЗ НОВИНОК/ТОПА ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('search_'))
def search_from_top(call):
    query = call.data.replace('search_', '')
    bot.answer_callback_query(call.id, "🔍 Ищу...")
    
    wait = bot.send_message(call.message.chat.id, "🔎 *Ищу трек...*", parse_mode='Markdown')
    result = search_music(query, call.message.chat.id)
    
    if result:
        markup, title = result
        bot.delete_message(call.message.chat.id, wait.message_id)
        bot.edit_message_text(
            f"🎵 *Результаты для:* {query}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.edit_message_text("❌ Трек не найден.", call.message.chat.id, wait.message_id)

# ========== ОТПРАВКА МУЗЫКИ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('mus_'))
def play_music(call):
    chat_id = call.message.chat.id
    tracks = user_results.get(chat_id, [])
    idx = int(call.data.split('_')[1])
    
    if idx >= len(tracks):
        bot.answer_callback_query(call.id, "❌ Трек не найден")
        return
    
    track = tracks[idx]
    url = track.get('webpage_url')
    title = track.get('title', 'Track')
    
    bot.answer_callback_query(call.id, "⏳ Скачиваю...")
    bot.edit_message_text(f"🎵 *{title}*\n⏳ Загрузка...", chat_id, call.message.message_id, parse_mode='Markdown')
    
    try:
        file_path = download_audio(url, title)
        with open(file_path, 'rb') as audio:
            bot.send_audio(chat_id, audio, title=title[:100])
        os.remove(file_path)
        bot.delete_message(chat_id, call.message.message_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {e}")

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("🎵 Музыкальный бот запущен!")
    bot.polling(none_stop=True)
