import telebot
from telebot import types
from soundcloudlib import SoundcloudAPI
import os

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎶 **Бот готов!** Попробуй найти любимый трек.", 
                     reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название:")
    else:
        q = "Top hits 2026" if "Популярное" in message.text else "New songs 2026"
        search_and_send(message, q)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_and_send(message, message.text)

def search_and_send(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    try:
        api = SoundcloudAPI()
        tracks = api.search(query)
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        track = tracks[0] # Берем самый первый результат
        bot.delete_message(message.chat.id, wait.message_id)
        
        # Отправляем инфо и ссылку
        text = f"🎵 **{track.artist} — {track.title}**\n\n🔗 [Слушать на SoundCloud]({track.permalink_url})"
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
        
    except Exception:
        bot.edit_message_text("⚠️ Ошибка связи с сервисом. Попробуй другой запрос.", message.chat.id, wait.message_id)

if __name__ == '__main__':
    bot.polling(none_stop=True)
