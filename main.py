import telebot
from telebot import types
import requests
import os
import yt_dlp

# ========== НАСТРОЙКИ ==========
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
VK_TOKEN = 'vk1.a.NKUmyxu4RrDruC7yN_35iEwEU8WbhMa6C0UeWYJ0t0thQO_SNI1Ct9OggV2GoDmhEoSyoGEMPLpznfx2YtxcAhfsw8e6Dl3wyphGQgLHLMVJWUs8Bp9fAzUK8YR_lM9TcmNwlY6gaDcg28WlTs2TuCifi5AitNSLK2TqALhV3HychnJBTFODv2MPkfp3k8ahab6o0UYEs9-VjB9EtIBNJg'
CHANNEL_ID = '-1001888094511'
CHANNEL_URL = 'https://t.me/lyubimkatt'

bot = telebot.TeleBot(TG_TOKEN)

user_tracks = {}

# ========== КНОПКИ ==========
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Поиск музыки")
    markup.add("🆕 Новинки", "🔥 Топ 100")
    return markup

# ========== ПРОВЕРКА ПОДПИСКИ ==========
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# ========== ПОИСК В VK ==========
def search_vk(query):
    try:
        url = 'https://api.vk.com/method/audio.search'
        params = {
            'q': query,
            'access_token': VK_TOKEN,
            'v': '5.131',
            'count': 10,
            'sort': 2  # 2 = по популярности
        }
        r = requests.get(url, params=params)
        data = r.json()
        if 'response' in data:
            return data['response']['items']
        return []
    except Exception as e:
        print(f"Ошибка VK: {e}")
        return []

# ========== НОВИНКИ (рекомендации VK) ==========
def get_new_tracks():
    try:
        # Метод getRecommendations возвращает новые треки
        url = 'https://api.vk.com/method/audio.getRecommendations'
        params = {
            'access_token': VK_TOKEN,
            'v': '5.131',
            'count': 10
        }
        r = requests.get(url, params=params)
        data = r.json()
        if 'response' in data:
            return data['response']['items']
        return []
    except:
        return []

# ========== ТОП 100 (популярное) ==========
def get_popular_tracks():
    try:
        url = 'https://api.vk.com/method/audio.getPopular'
        params = {
            'access_token': VK_TOKEN,
            'v': '5.131',
            'count': 10
        }
        r = requests.get(url, params=params)
        data = r.json()
        if 'response' in data:
            return data['response']['items']
        return []
    except:
        return []

# ========== СКАЧИВАНИЕ MP3 ИЗ VK ==========
def download_vk_mp3(url, title):
    """Скачивает MP3 из VK"""
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

# ========== ПОКАЗ ТРЕКОВ ==========
def show_tracks(chat_id, tracks, title):
    if not tracks:
        bot.send_message(chat_id, "❌ Ничего не найдено.")
        return
    
    user_tracks[chat_id] = tracks
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, track in enumerate(tracks[:10]):
        artist = track.get('artist', 'Unknown')
        title_track = track.get('title', 'Track')
        button_text = f"🎵 {artist} - {title_track[:40]}"
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=f"play_{i}"))
    
    bot.send_message(chat_id, f"🎵 *{title}*", reply_markup=markup, parse_mode='Markdown')

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub"))
        bot.send_message(message.chat.id, "⚠️ *Доступ закрыт!*\n\nПодпишись на канал.", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "🎵 *Муз-бот готов!*", reply_markup=main_menu(), parse_mode='Markdown')

# ========== ПОИСК ==========
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
    tracks = search_vk(message.text)
    
    if tracks:
        bot.delete_message(message.chat.id, wait.message_id)
        show_tracks(message.chat.id, tracks, f"Результаты: {message.text}")
    else:
        bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)

# ========== НОВИНКИ ==========
@bot.message_handler(func=lambda msg: msg.text == "🆕 Новинки")
def new_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    
    wait = bot.send_message(message.chat.id, "🔎 *Загружаю новинки...*", parse_mode='Markdown')
    tracks = get_new_tracks()
    
    if tracks:
        bot.delete_message(message.chat.id, wait.message_id)
        show_tracks(message.chat.id, tracks, "🆕 Новинки российской музыки")
    else:
        bot.edit_message_text("❌ Не удалось загрузить новинки.", message.chat.id, wait.message_id)

# ========== ТОП 100 ==========
@bot.message_handler(func=lambda msg: msg.text == "🔥 Топ 100")
def top_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    
    wait = bot.send_message(message.chat.id, "🔎 *Загружаю топ...*", parse_mode='Markdown')
    tracks = get_popular_tracks()
    
    if tracks:
        bot.delete_message(message.chat.id, wait.message_id)
        show_tracks(message.chat.id, tracks, "🔥 Топ 100")
    else:
        bot.edit_message_text("❌ Не удалось загрузить топ.", message.chat.id, wait.message_id)

# ========== СКАЧИВАНИЕ И ОТПРАВКА ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def play_track(call):
    idx = int(call.data.split('_')[1])
    tracks = user_tracks.get(call.message.chat.id, [])
    
    if idx >= len(tracks):
        bot.answer_callback_query(call.id, "❌ Трек не найден")
        return
    
    track = tracks[idx]
    artist = track.get('artist', 'Unknown')
    title = track.get('title', 'Track')
    url = track.get('url')
    
    if not url:
        bot.answer_callback_query(call.id, "❌ Ссылка на трек недоступна")
        return
    
    bot.answer_callback_query(call.id, f"⏳ Скачиваю: {artist} - {title}")
    
    status_msg = bot.send_message(call.message.chat.id, f"🎵 *{artist} - {title}*\n⏳ Скачивание...", parse_mode='Markdown')
    
    try:
        file_path = download_vk_mp3(url, f"{artist} - {title}")
        with open(file_path, 'rb') as audio:
            bot.send_audio(call.message.chat.id, audio, title=title, performer=artist)
        os.remove(file_path)
        bot.delete_message(call.message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, status_msg.message_id)

# ========== ПРОВЕРКА ПОДПИСКИ ==========
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_callback(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Подписка подтверждена!")
        bot.edit_message_text("🎉 Спасибо! Теперь ты можешь слушать музыку.", call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "🎵 *Муз-бот готов!*", reply_markup=main_menu(), parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписаны!", show_alert=True)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("🎵 VK Music Bot (скачивание MP3) запущен!")
    bot.polling(none_stop=True)
