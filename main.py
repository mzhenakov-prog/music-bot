import telebot
from telebot import types
import yt_dlp

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки для поиска именно ПЕСЕН, а не видео-миксов
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch15', # Ищем 15 вариантов
    'geo_bypass': True,
    'extract_flat': False,
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
        "Я найду именно треки в формате: *Исполнитель — Название*."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Введите название:")
    elif message.text == "🚀 Популярное":
        # Уточняем запрос, чтобы не вылезали миксы
        search_engine(message, "Top Russian Hits Official Audio")
    elif message.text == "✨ Новинки":
        search_engine(message, "Новинки музыки СНГ 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_engine(message, message.text)

def search_engine(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу треки...*")
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Ищем музыку, исключая видео-миксы
            search_query = f"{query} audio"
            info = ydl.extract_info(f"ytsearch15:{search_query}", download=False)
            tracks = info['entries']
            
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks):
            title = track.get('title', 'Unknown')
            # ЧИСТКА НАЗВАНИЯ: убираем мусор, чтобы было Артист - Название
            clean_title = title.replace("Official Video", "").replace("Official Audio", "").replace("(Lyric Video)", "").replace("2026", "").replace("2025", "")
            clean_title = clean_title.split('|')[0].split('(')[0].strip()
            
            display_text = (clean_title[:45] + '..') if len(clean_title) > 45 else clean_title
            markup.add(types.InlineKeyboardButton(text=display_text, callback_data=f"tr_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 Результаты для: *{query}*", reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tr_'))
def send_music(call):
    idx = int(call.data.split('_')[1])
    track = user_results[call.message.chat.id][idx]
    
    # Прямая ссылка на аудио
    url = track['url']
    full_title = track.get('title', 'Music')

    bot.answer_callback_query(call.id, "📥 Отправляю в плеер...")
    
    # Пытаемся разделить на Артиста и Название
    if " - " in full_title:
        performer, title = full_title.split(" - ", 1)
    elif " — " in full_title:
        performer, title = full_title.split(" — ", 1)
    else:
        performer, title = "VK Music", full_title

    # Очищаем от мусора финальные теги для плеера
    clean_title = title.split('(')[0].split('[')[0].strip()

    bot.send_audio(
        call.message.chat.id, 
        url, 
        title=clean_title, 
        performer=performer.strip(),
        caption=f"🎧 **{performer.strip()} — {clean_title}**",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
