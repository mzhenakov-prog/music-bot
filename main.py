import telebot
from telebot import types
import requests

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    about_text = (
        "👋 **Привет! Я твой музыкальный помощник.**\n\n"
        "📥 Ищу лучшие треки из топ-чартов СНГ.\n"
        "🔥 **В разделах Популярное и Новинки только свежие хиты!**\n\n"
        "Просто выбери категорию или напиши название песни."
    )
    bot.send_message(message.chat.id, about_text, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название артиста или песни:")
    elif message.text == "🚀 Популярное":
        # Используем ключевые слова для поиска аналога чарта ВК
        search_music(message, "Top Hits Russia VK")
    elif message.text == "✨ Новинки":
        # Поиск самых свежих релизов
        search_music(message, "Новинки музыки 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_music(message, message.text)

def search_music(message, query):
    try:
        # Поиск через стабильный Deezer
        response = requests.get(f"https://api.deezer.com/search?q={query}&limit=10").json()
        if not response.get('data'):
            bot.send_message(message.chat.id, "❌ Ничего не найдено.")
            return

        tracks = response['data']
        user_results[message.chat.id] = tracks
        
        markup = types.InlineKeyboardMarkup()
        for i, track in enumerate(tracks):
            # Кнопка как на скриншоте: Артист — Название
            btn_text = f"{track['artist']['name']} — {track['title']}"
            markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"tr_{i}"))
        
        bot.send_message(message.chat.id, f"🎶 Результаты по запросу: *{query}*", 
                         reply_markup=markup, parse_mode='Markdown')
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Ошибка. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tr_'))
def send_track(call):
    idx = int(call.data.split('_')[1])
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "Поищи заново.")
        return

    track = user_results[call.message.chat.id][idx]
    
    # Исправляем отображение (убираем рандомные буквы из плеера)
    artist_name = track['artist']['name']
    track_title = track['title']
    audio_url = track['preview']

    bot.answer_callback_query(call.id, f"🎵 {track_title}")
    
    bot.send_audio(
        call.message.chat.id, 
        audio_url, 
        title=track_title, 
        performer=artist_name,
        caption=f"✅ {artist_name} — {track_title}"
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
