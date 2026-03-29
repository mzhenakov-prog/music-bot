import telebot
from telebot import types
from sclib import SoundcloudAPI
import os

# Твой токен уже на месте!
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'

bot = telebot.TeleBot(TG_TOKEN)
api = SoundcloudAPI()

# Временное хранилище для треков, чтобы бот знал, что скачивать
user_cache = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔥 ТОП Чарт", "🆕 Новинки")
    bot.send_message(
        message.chat.id, 
        "🎵 **Музыкальный бот SoundCloud запущен!**\n\nНапиши название песни или артиста, и я найду лучшие варианты.", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text in ["🔥 ТОП Чарт", "🆕 Новинки"])
def handle_charts(message):
    query = "Top Hits" if "ТОП" in message.text else "New Music"
    search_and_send(message, query)

@bot.message_handler(content_types=['text'])
def handle_search(message):
    # Пропускаем, если нажата кнопка меню
    if message.text in ["🔥 ТОП Чарт", "🆕 Новинки"]:
        return
    search_and_send(message, message.text)

def search_and_send(message, query):
    wait_msg = bot.send_message(message.chat.id, "🔍 Ищу лучшие треки...")
    try:
        # Ищем 6 вариантов
        tracks = list(api.search_tracks(query))[:6]
        
        if not tracks:
            bot.edit_message_text("Ничего не найдено 😔 Попробуй другой запрос.", message.chat.id, wait_msg.message_id)
            return

        user_cache[message.chat.id] = tracks
        
        response_text = f"🎶 **Результаты по запросу:** _{query}_\n\n"
        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = []

        for i, track in enumerate(tracks, 1):
            response_text += f"{i}. {track.artist} — {track.title}\n"
            buttons.append(types.InlineKeyboardButton(text=str(i), callback_data=f"sc_{i-1}"))
        
        markup.add(*buttons)
        bot.delete_message(message.chat.id, wait_msg.message_id)
        bot.send_message(message.chat.id, response_text, reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        print(f"Ошибка поиска: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при поиске. Попробуй позже.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sc_'))
def handle_download(call):
    index = int(call.data.split('_')[1])
    user_id = call.message.chat.id
    
    if user_id not in user_cache:
        bot.answer_callback_query(call.id, "Результаты устарели, поищи заново.")
        return

    track = user_cache[user_id][index]
    bot.answer_callback_query(call.id, "🚀 Начинаю загрузку...")
    
    file_path = f"{track.id}.mp3"
    try:
        # Скачиваем во временный файл
        with open(file_path, 'wb+') as fp:
            track.write_mp3_to(fp)
        
        # Отправляем аудио пользователю
        with open(file_path, 'rb') as audio:
            bot.send_audio(
                user_id, 
                audio, 
                title=track.title, 
                performer=track.artist,
                caption=f"🎧 Найдено через бота"
            )
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        bot.send_message(user_id, "❌ Не удалось скачать этот трек.")
    finally:
        # Удаляем файл с хостинга, чтобы не занимать место
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    print("Бот в эфире!")
    bot.polling(none_stop=True)
