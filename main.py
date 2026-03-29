import telebot
from telebot import types
import yt_dlp
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
    bot.send_message(message.chat.id, "🎵 **Музыкальный бот готов к работе!**", 
                     reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название трека:")
    else:
        query = "популярная музыка 2026" if "Популярное" in message.text else "новинки музыки 2026"
        search_music(message, query)

@bot.message_handler(content_types=['text'])
def text_search(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_music(message, message.text)

def search_music(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу музыку...* (это может занять 5-10 сек)", parse_mode='Markdown')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch1',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"
            
            # Переименовываем в mp3 если скачалось в другом формате
            actual_file = ydl.prepare_filename(info)
            if os.path.exists(actual_file):
                os.rename(actual_file, filename)

            with open(filename, 'rb') as audio:
                bot.delete_message(message.chat.id, wait.message_id)
                bot.send_audio(message.chat.id, audio, title=info.get('title'), performer=info.get('uploader'))
            
            if os.path.exists(filename):
                os.remove(filename)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: Не удалось найти или скачать. Попробуй другой запрос.", 
                              message.chat.id, wait.message_id)

if __name__ == '__main__':
    bot.polling(none_stop=True)
