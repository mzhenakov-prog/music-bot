import telebot
from telebot import types
import yt_dlp

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки для получения ПОЛНЫХ треков
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch15',
    'geo_bypass': True,
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
        "👋 **Добро пожаловать в VK Music!**\n\n"
        "Здесь ты найдешь только полные треки и свежие чарты СНГ.\n\n"
        "ℹ️ **Инструкция:**\n"
        "Просто напиши название или выбери раздел ниже."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ **Напиши название или артиста:**", parse_mode='Markdown')
    elif message.text == "🚀 Популярное":
        search_engine(message, "Russian Music Charts 2026")
    elif message.text == "✨ Новинки":
        search_engine(message, "Новинки музыки Россия СНГ 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_engine(message, message.text)

def search_engine(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу полные версии треков...*", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Ищем сразу много вариантов
            info = ydl.extract_info(f"ytsearch15:{query}", download=False)
            tracks = info['entries']
            
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks):
            title = track.get('title', 'Без названия')
            # Очистка названия для красоты
            clean_title = title.split('(')[0].split('[')[0].strip()[:45]
            markup.add(types.InlineKeyboardButton(text=clean_title, callback_data=f"play_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 Результаты для: *{query}*", reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def send_audio(call):
    idx = int(call.data.split('_')[1])
    track = user_results[call.message.chat.id][idx]
    
    # Прямая ссылка на аудиопоток (ВСЕГДА ПОЛНАЯ ВЕРСИЯ)
    audio_url = track['url']
    full_title = track.get('title', 'Music')
    
    # Пытаемся красиво разбить на Артиста и Название
    if " - " in full_title:
        performer, title = full_title.split(" - ", 1)
    elif " — " in full_title:
        performer, title = full_title.split(" — ", 1)
    else:
        performer, title = "VK Music", full_title

    bot.answer_callback_query(call.id, "📥 Загружаю полный трек...")
    
    # Отправка в ПЛЕЕР (не файлом!)
    bot.send_audio(
        call.message.chat.id, 
        audio_url, 
        title=title.strip(), 
        performer=performer.strip(),
        caption=f"🎧 **{performer.strip()} — {title.strip()}**",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
