import telebot
from telebot import types
from sclib import SoundcloudAPI, Track
import os

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)
api = SoundcloudAPI()

user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    about = (
        "👋 **Музыкальный бот запущен!**\n\n"
        "Напиши название песни или артиста, и я найду лучшие варианты."
    )
    bot.send_message(message.chat.id, about, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название трека:")
    elif message.text == "🚀 Популярное":
        search_sc(message, "Russian Top Chart 2026")
    elif message.text == "✨ Новинки":
        search_sc(message, "Новинки музыки Россия 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_sc(message, message.text)

def search_sc(message, query):
    wait = bot.send_message(message.chat.id, "🔍 *Ищу лучшие треки...*", parse_mode='Markdown')
    try:
        # Ищем треки через SoundCloud
        tracks = api.search_tracks(query)
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        # Берем первые 10 результатов
        results = tracks[:10]
        user_results[message.chat.id] = results
        
        markup = types.InlineKeyboardMarkup()
        for i, track in enumerate(results):
            # Формат кнопки: Исполнитель — Название (как на твоем скрине)
            label = f"{track.artist} — {track.title}"
            # Укорачиваем, если слишком длинно
            short_label = (label[:40] + '..') if len(label) > 40 else label
            markup.add(types.InlineKeyboardButton(text=short_label, callback_data=f"sc_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, "🔥 **Топ Музыки**", reply_markup=markup, parse_mode='Markdown')
    except Exception:
        bot.edit_message_text("❌ Произошла ошибка при поиске. Попробуй позже.", message.chat.id, wait.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sc_'))
def send_music(call):
    idx = int(call.data.split('_')[1])
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "Поищи заново.")
        return

    track = user_results[call.message.chat.id][idx]
    bot.answer_callback_query(call.id, "📥 Отправляю файл...")

    try:
        # Скачиваем и отправляем реальный аудиофайл
        filename = f"{track.artist} - {track.title}.mp3"
        with open(filename, 'wb+') as fp:
            track.write_to(fp)
        
        with open(filename, 'rb') as audio:
            bot.send_audio(
                call.message.chat.id, 
                audio, 
                title=track.title, 
                performer=track.artist,
                caption=f"✅ {track.artist} — {track.title}"
            )
        # Удаляем файл после отправки, чтобы не забивать Bothost
        os.remove(filename)
    except Exception:
        bot.send_message(call.message.chat.id, "❌ Не удалось скачать этот трек.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
