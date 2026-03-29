import telebot
from telebot import types
import yt_dlp
import os

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки для скачивания именно ПЕСНИ
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'outtmpl': '/tmp/%(id)s.%(ext)s', # Качаем во временную папку
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'match_filter': yt_dlp.utils.match_filter_func("duration < 400"),
}

user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔥 ТОП Чарты"), types.KeyboardButton("🆕 Новинки недели"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎵 **Музыкальный Бот запущен!**\n\nПришлю трек в плеер Telegram. Просто напиши название.", reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск музыки")
def search_hint(message):
    bot.send_message(message.chat.id, "⌨️ **Напиши название песни или артиста:**", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔥 ТОП Чарты")
def chart_logic(message):
    search_engine(message, "Top Hits 2026 Russia")

@bot.message_handler(func=lambda m: m.text == "🆕 Новинки недели")
def news_logic(message):
    search_engine(message, "Новинки музыки 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🔥 ТОП Чарты", "🆕 Новинки недели", "🔍 Поиск музыки"]:
        search_engine(message, message.text)

def search_engine(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу треки...*")
    try:
        with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True, 'default_search': 'ytsearch10', 'noplaylist': True}) as ydl:
            info = ydl.extract_info(query, download=False)
            tracks = [e for e in info['entries'] if e]
            
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        for i, track in enumerate(tracks[:8]):
            title = track.get('title', 'Track')[:40]
            markup.add(types.InlineKeyboardButton(text=f"▶️ {title}", callback_data=f"tr_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 Результаты для: *{query}*", reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tr_'))
def send_music(call):
    idx = int(call.data.split('_')[1])
    track_info = user_results[call.message.chat.id][idx]
    url = track_info['webpage_url']
    
    bot.answer_callback_query(call.id, "📥 Начинаю загрузку трека...")
    wait = bot.send_message(call.message.chat.id, "⏳ *Подожди пару секунд, загружаю в плеер...*", parse_mode='Markdown')

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
            
            # Отправка в плеер
            with open(filename, 'rb') as audio:
                bot.send_audio(
                    call.message.chat.id, 
                    audio, 
                    title=info.get('title', 'Music'), 
                    performer="VK Music",
                    caption="✅ Приятного прослушивания!"
                )
            
            bot.delete_message(call.message.chat.id, wait.message_id)
            if os.path.exists(filename):
                os.remove(filename) # Удаляем файл, чтобы не занимать место

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Ошибка загрузки: файл слишком большой или недоступен.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
