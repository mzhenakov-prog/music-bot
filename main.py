import telebot
from telebot import types
import yt_dlp

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки: фильтруем всё, что длиннее 360 секунд (6 минут)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch20',
    'geo_bypass': True,
    # Игнорируем длинные видео (миксы)
    'match_filter': yt_dlp.utils.match_filter_func("duration < 360"), 
}

user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        "👋 **VK Music Search**\n\n"
        "Напиши название песни или артиста.\n"
        "Я нахожу только полные треки (до 6 мин), без длинных миксов."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ **Введите название:**", parse_mode='Markdown')
    elif message.text == "🚀 Популярное":
        search_engine(message, "Top Hits Russia Official Audio")
    elif message.text == "✨ Новинки":
        search_engine(message, "Новинки музыки 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_engine(message, message.text)

def search_engine(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Фильтруем миксы и ищем трек...*", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Добавляем "audio", чтобы искать именно песни
            info = ydl.extract_info(f"ytsearch20:{query} audio", download=False)
            # Фильтруем результаты еще раз вручную для надежности
            tracks = [entry for entry in info['entries'] if entry and entry.get('duration', 0) < 400]
            
        if not tracks:
            bot.edit_message_text("❌ Подходящие треки не найдены (миксы проигнорированы).", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks[:15]):
            title = track.get('title', 'Unknown')
            # Чистим название от мусора
            clean_title = title.split('|')[0].split('(')[0].split('[')[0].strip()
            display_text = (clean_title[:45] + '..') if len(clean_title) > 45 else clean_title
            markup.add(types.InlineKeyboardButton(text=display_text, callback_data=f"tr_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 Результаты для: *{query}*", reply_markup=markup, parse_mode='Markdown')
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска. Попробуй другой запрос.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tr_'))
def send_music(call):
    idx = int(call.data.split('_')[1])
    track = user_results[call.message.chat.id][idx]
    
    bot.answer_callback_query(call.id, "📥 Отправляю трек в плеер...")
    
    # Прямая ссылка на аудио
    url = track['url']
    full_title = track.get('title', 'Music')

    # Красиво разбиваем на Исполнитель - Название
    if " - " in full_name := full_title:
        performer, title = full_name.split(" - ", 1)
    elif " — " in full_name:
        performer, title = full_name.split(" — ", 1)
    else:
        performer, title = "VK Music", full_name

    bot.send_audio(
        call.message.chat.id, 
        url, 
        title=title.split('(')[0].strip(), 
        performer=performer.strip(),
        caption=f"✅ **{performer.strip()} — {title.split('(')[0].strip()}**",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
