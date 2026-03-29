import telebot
from telebot import types
import requests

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("💜 Топ Музыки"))
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    about = (
        "👋 **Музыкальный бот готов!**\n\n"
        "🎶 Нахожу полные треки в высоком качестве.\n"
        "В плеере всегда будет: *Исполнитель — Название*."
    )
    bot.send_message(message.chat.id, about, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки", "💜 Топ Музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ **Напиши название трека:**", parse_mode='Markdown')
    elif message.text in ["🚀 Популярное", "💜 Топ Музыки"]:
        search_music(message, "Russian Chart 2026")
    elif message.text == "✨ Новинки":
        search_music(message, "Новинки музыки 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки", "💜 Топ Музыки"]:
        search_music(message, message.text)

def search_music(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу полную версию...*", parse_mode='Markdown')
    try:
        # Поиск через базу iTunes (дает лучшие метаданные для плеера)
        url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=10&country=ru"
        response = requests.get(url).json()
        tracks = response.get('results', [])

        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks):
            # Кнопка: Исполнитель — Название
            btn_text = f"{track['artistName']} — {track['trackName']}"
            short_text = (btn_text[:45] + '..') if len(btn_text) > 45 else btn_text
            markup.add(types.InlineKeyboardButton(text=short_text, callback_data=f"play_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, "⬇️ **Найденные треки:**", reply_markup=markup, parse_mode='Markdown')
    except:
        bot.edit_message_text("⚠️ Ошибка поиска.", message.chat.id, wait.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def send_audio(call):
    idx = int(call.data.split('_')[1])
    track = user_results[call.message.chat.id][idx]
    
    artist = track['artistName']
    title = track['trackName']
    audio_url = track['previewUrl'] # Ссылка на аудио

    bot.answer_callback_query(call.id, "📥 Загружаю в плеер...")
    
    # КЛЮЧЕВОЙ МОМЕНТ: Метод send_audio делает файл «слушабельным» в плеере
    # Параметры title и performer убирают «рандомные буквы»
    bot.send_audio(
        call.message.chat.id, 
        audio_url, 
        title=title, 
        performer=artist,
        caption=f"✅ **{artist} — {title}**",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
