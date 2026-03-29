import telebot
from telebot import types
import requests

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Временное хранилище результатов
user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🇷🇺 **Топ-чарты и поиск музыки готовы!**", 
                     reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название артиста или песни (например: *Три дня дождя*):", parse_mode='Markdown')
    elif message.text == "🚀 Популярное":
        # Запрос на самые горячие хиты РФ (рэп и поп чарты)
        search_music(message, "Top Russian Hits 2026")
    elif message.text == "✨ Новинки":
        # Запрос на свежие релизы
        search_music(message, "Новинки музыки Россия 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_music(message, message.text)

def search_music(message, query):
    try:
        # Увеличили лимит до 10 для выбора
        response = requests.get(f"https://api.deezer.com/search?q={query}&limit=10").json()
        if not response.get('data'):
            bot.send_message(message.chat.id, "❌ Ничего не найдено по этому запросу.")
            return

        tracks = response['data']
        user_results[message.chat.id] = tracks
        
        markup = types.InlineKeyboardMarkup()
        for i, track in enumerate(tracks):
            # Текст на кнопке: Артист - Трек
            btn_text = f"{track['artist']['name']} — {track['title']}"
            markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"tr_{i}"))
        
        bot.send_message(message.chat.id, f"🎵 Найдено по запросу: *{query}*", 
                         reply_markup=markup, parse_mode='Markdown')
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Ошибка связи. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tr_'))
def send_track(call):
    idx = int(call.data.split('_')[1])
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "Поиск устарел, введи название снова.")
        return

    track = user_results[call.message.chat.id][idx]
    
    # Данные для плеера
    artist = track['artist']['name']
    title = track['title']
    url = track['preview']

    bot.answer_callback_query(call.id, f"📥 Загружаю: {title}")
    
    # Отправляем аудио с ЧЕТКИМИ названиями артиста и песни
    bot.send_audio(
        call.message.chat.id, 
        url, 
        title=title, 
        performer=artist,
        caption=f"🎧 **{artist} — {title}**",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)

