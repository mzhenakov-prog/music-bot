import telebot
from telebot import types
import requests

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Временное хранилище
user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "👋 **Музыкальный поиск готов.**\nНайду любой трек по названию или артисту.", 
        reply_markup=main_menu(), 
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название песни или имя артиста:")
    elif message.text == "🚀 Популярное":
        # Поиск по глобальному российскому чарту
        search_engine(message, "Russian Chart Top 100", is_chart=True)
    elif message.text == "✨ Новинки":
        # Поиск самых свежих релизов
        search_engine(message, "Russian New Music 2026", is_chart=True)

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_engine(message, message.text)

def search_engine(message, query, is_chart=False):
    wait = bot.send_message(message.chat.id, "🔎 *Поиск в базе данных...*", parse_mode='Markdown')
    try:
        # Используем базу с фильтром по региону для точности чартов
        url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=15&country=ru"
        response = requests.get(url).json()
        tracks = response.get('results', [])

        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено. Попробуй уточнить запрос.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks):
            # Красивый формат: Артист - Название
            artist = track.get('artistName', 'Артист')
            title = track.get('trackName', 'Трек')
            btn_text = f"{artist} — {title}"
            
            # Обрезаем длинные названия
            display_text = (btn_text[:45] + '..') if len(btn_text) > 45 else btn_text
            markup.add(types.InlineKeyboardButton(text=display_text, callback_data=f"sel_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        msg_text = "📈 **Топ чарт:**" if is_chart else f"🔍 **Результаты по запросу '{query}':**"
        bot.send_message(message.chat.id, msg_text, reply_markup=markup, parse_mode='Markdown')
        
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sel_'))
def send_music(call):
    idx = int(call.data.split('_')[1])
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "Результаты устарели.")
        return

    track = user_results[call.message.chat.id][idx]
    
    artist = track.get('artistName')
    title = track.get('trackName')
    audio_url = track.get('previewUrl')

    bot.answer_callback_query(call.id, f"📥 Загружаю: {title}")
    
    # ОТПРАВКА КАК АУДИО (ПЛЕЕР)
    # title и performer убирают рандомные буквы в плеере
    bot.send_audio(
        call.message.chat.id, 
        audio_url, 
        title=title, 
        performer=artist,
        caption=f"🎧 **{artist} — {title}**",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
