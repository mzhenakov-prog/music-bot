import telebot
from telebot import types
import requests

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Хранилище результатов
user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    about = "🎵 **Музыкальный поиск ВК & СНГ**\n\nНапиши название или артиста. Я найду все варианты!"
    bot.send_message(message.chat.id, about, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Введи название:")
    elif message.text == "🚀 Популярное":
        fast_search(message, "Russian Top Hits 2026")
    elif message.text == "✨ Новинки":
        fast_search(message, "Новинки СНГ 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        fast_search(message, message.text)

def fast_search(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу...*", parse_mode='Markdown')
    try:
        # Используем очень быстрое API (iTunes/Apple Music база - самая точная по СНГ)
        url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=20&country=ru"
        res = requests.get(url).json()
        tracks = res.get('results', [])

        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks):
            # Формат кнопки: Артист - Название
            artist = track.get('artistName', 'Артист')
            title = track.get('trackName', 'Трек')
            btn_text = f"{artist} — {title}"
            
            # Обрезаем, если слишком длинно
            short_text = (btn_text[:45] + '..') if len(btn_text) > 45 else btn_text
            markup.add(types.InlineKeyboardButton(text=short_text, callback_data=f"aud_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 Результаты для: *{query}*", 
                         reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка связи.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('aud_'))
def send_audio(call):
    idx = int(call.data.split('_')[1])
    track = user_results[call.message.chat.id][idx]
    
    artist = track.get('artistName')
    title = track.get('trackName')
    audio_url = track.get('previewUrl') # Прямая ссылка на поток

    bot.answer_callback_query(call.id, "📥 Отправляю...")
    
    # Отправка как Аудио (Плеер с кнопкой Play)
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
