import telebot
from telebot import types
import requests

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Временное хранилище для найденных треков
user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎵 **Музыкальный поиск готов!**\nНапиши название песни или выбери в меню.", 
                     reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название артиста или песни:")
    else:
        # Для категорий используем понятные запросы
        q = "russian hits" if "Популярное" in message.text else "latest releases"
        search_music(message, q)

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_music(message, message.text)

def search_music(message, query):
    try:
        # Ищем музыку в Deezer
        response = requests.get(f"https://api.deezer.com/search?q={query}&limit=10").json()
        
        if not response.get('data'):
            bot.send_message(message.chat.id, "❌ Ничего не найдено.")
            return

        tracks = response['data']
        user_results[message.chat.id] = tracks # Сохраняем, чтобы потом скачать по кнопке
        
        markup = types.InlineKeyboardMarkup()
        # Создаем кнопки как на твоем скриншоте
        for i, track in enumerate(tracks):
            btn_text = f"{track['artist']['name']} — {track['title']}"
            markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"track_{i}"))
        
        bot.send_message(message.chat.id, f"🎶 Результаты по запросу: *{query}*", 
                         reply_markup=markup, parse_mode='Markdown')

    except Exception:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('track_'))
def send_track(call):
    index = int(call.data.split('_')[1])
    user_id = call.message.chat.id
    
    if user_id not in user_results:
        bot.answer_callback_query(call.id, "Результаты устарели, поищи еще раз.")
        return

    track_data = user_results[user_id][index]
    artist = track_data['artist']['name']
    title = track_data['title']
    preview_url = track_data['preview']

    bot.answer_callback_query(call.id, "🚀 Отправляю...")
    
    # Отправляем аудио с правильным названием артиста и песни
    bot.send_audio(user_id, preview_url, title=title, performer=artist)

if __name__ == '__main__':
    bot.polling(none_stop=True)
