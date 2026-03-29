import telebot
from telebot import types
import requests

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
    bot.send_message(message.chat.id, "🎵 **Музыкальный поиск Deezer готов!**\n\nПросто напиши название песни.", 
                     reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def handle_menu(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название артиста или песни:")
    else:
        query = "chart" if "Популярное" in message.text else "new hits"
        search_deezer(message, query)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_deezer(message, message.text)

def search_deezer(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу в базе Deezer...*", parse_mode='Markdown')
    try:
        # Прямой запрос к API Deezer (бесплатно и без ключей)
        response = requests.get(f"https://api.deezer.com/search?q={query}&limit=5").json()
        
        if not response.get('data'):
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        bot.delete_message(message.chat.id, wait.message_id)

        for track in response['data']:
            title = track['title']
            artist = track['artist']['name']
            preview = track['preview'] # Ссылка на 30 сек превью
            link = track['link'] # Ссылка на полный трек
            cover = track['album']['cover_medium']

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔗 Полная версия", url=link))
            
            caption = f"🎶 **{artist} — {title}**"
            
            # Отправляем карточку с обложкой и аудио-превью
            bot.send_photo(message.chat.id, cover, caption=caption, reply_markup=markup, parse_mode='Markdown')
            bot.send_audio(message.chat.id, preview, title=title, performer=artist)

    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска. Попробуй еще раз.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
