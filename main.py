import telebot
from telebot import types
import yt_dlp

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки для поиска именно полных аудио-версий (Official Audio)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch10',
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
    about = (
        "👋 **Музыкальный бот 2026**\n\n"
        "🔥 Здесь только полные треки из чартов ВК и YouTube.\n"
        "Обновление чартов происходит ежедневно!"
    )
    bot.send_message(message.chat.id, about, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название:")
    elif message.text == "🚀 Популярное":
        # Ищем именно в российском чарте YouTube/ВК
        search_youtube(message, "Top 100 Russia 2026 Official Audio")
    elif message.text == "✨ Новинки":
        # Ищем самые свежие релизы этой недели
        search_youtube(message, "Новинки музыки Россия СНГ 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_youtube(message, message.text)

def search_youtube(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Синхронизация с чартами...*", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Ищем 10 вариантов, чтобы отсечь лишнее
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)
            tracks = info['entries']
            
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks):
            title = track.get('title', 'Без названия')
            # Убираем из названия лишние слова типа "Official Video", чтобы было красиво
            clean_title = title.replace("(Official Video)", "").replace("Official Audio", "").replace("|", "-")
            btn_text = (clean_title[:45] + '..') if len(clean_title) > 45 else clean_title
            markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"yt_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎵 Актуально по запросу: *{query}*", 
                         reply_markup=markup, parse_mode='Markdown')
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Ошибка обновления чарта. Попробуй позже.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('yt_'))
def send_track(call):
    idx = int(call.data.split('_')[1])
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "Поищи заново.")
        return

    track_info = user_results[call.message.chat.id][idx]
    url = track_info['url']
    title = track_info.get('title', 'Music track')

    bot.answer_callback_query(call.id, "📥 Загрузка полной версии...")
    
    # Отправляем аудио. Плеер Telegram подхватит название из заголовка YouTube
    bot.send_audio(
        call.message.chat.id, 
        url, 
        title=title,
        performer="TOP 2026",
        caption=f"✅ Полная версия: {title}"
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
