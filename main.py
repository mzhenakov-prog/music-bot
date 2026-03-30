import telebot
from telebot import types
import yt_dlp
import os

# ========== НАСТРОЙКИ ==========
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
CHANNEL_ID = '-100XXXXXXXXXX'  # Замени на ID своего канала
CHANNEL_URL = 'https://t.me/твой_канал'  # Ссылка на канал

bot = telebot.TeleBot(TG_TOKEN)

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch10',
    'match_filter': yt_dlp.utils.match_filter_func("duration < 420"),
}

user_results = {}

# ========== ПРОВЕРКА ПОДПИСКИ ==========
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# ========== СКАЧИВАНИЕ АУДИО ==========
def download_audio(url, title):
    """Скачивает аудио и возвращает путь к файлу"""
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

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎶 **Муз-бот готов!**\nНапиши название песни, чтобы найти её.", parse_mode='Markdown')

# ========== ПОИСК ==========
@bot.message_handler(content_types=['text'])
def handle_search(message):
    # Проверка подписки
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub"))
        bot.send_message(
            message.chat.id,
            "⚠️ **Доступ закрыт!**\n\nЧтобы искать и слушать музыку, подпишись на наш канал.",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        return

    wait = bot.send_message(message.chat.id, "🔎 *Ищу треки...*", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"{message.text} audio", download=False)
            tracks = [e for e in info['entries'] if e]

        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, track in enumerate(tracks[:8]):
            title = track.get('title', 'Track')[:45]
            markup.add(types.InlineKeyboardButton(text=f"🎵 {title}", callback_data=f"mus_{i}"))

        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎵 *Результаты для:* {message.text}", reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка поиска: {e}")

# ========== ПРОВЕРКА ПОДПИСКИ ПОСЛЕ НАЖАТИЯ ==========
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_callback(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Подписка подтверждена!")
        bot.edit_message_text("🎉 Спасибо за подписку! Теперь присылай название песни.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Вы всё еще не подписаны!", show_alert=True)

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
