import telebot
from telebot import types
from sclib import SoundcloudAPI
import os
import time

# Твой токен (уже вставлен)
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'

bot = telebot.TeleBot(TG_TOKEN)

# Временное хранилище для треков, чтобы не искать дважды
user_cache = {}

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Кнопки со смайликами в удобном расположении
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

# --- ОБРАБОТЧИКИ ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "👋 **Привет! Твой персональный SoundCloud плеер готов.**\n\nИспользуй кнопки внизу или просто напиши название песни!",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def handle_menu(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название песни или имя артиста (например: *LSP*):", parse_mode='Markdown')
        return
    
    # Авто-запросы для чартов
    query = "Top Hits 2026" if "Популярное" in message.text else "New Rap Pop 2026"
    perform_search(message, query)

@bot.message_handler(content_types=['text'])
def handle_text_search(message):
    # Если юзер просто прислал текст — ищем его
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        perform_search(message, message.text)

def perform_search(message, query):
    # Показываем статус "поиск"
    wait_msg = bot.send_message(message.chat.id, f"🔎 *Ищу треки по запросу:* _{query}_...", parse_mode='Markdown')
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        api = SoundcloudAPI() 
        search_results = list(api.search_tracks(query))
        tracks = search_results[:6] # Берем первые 6 результатов
        
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено. Попробуй изменить запрос.", message.chat.id, wait_msg.message_id)
            return

        user_cache[message.chat.id] = tracks
        
        response_text = f"🎶 **Вот что я нашел:**\n\n"
        markup = types.InlineKeyboardMarkup(row_width=3)
        btns = []

        for i, track in enumerate(tracks, 1):
            response_text += f"{i}. {track.artist} — {track.title}\n"
            btns.append(types.InlineKeyboardButton(text=f"[{i}]", callback_data=f"dl_{i-1}"))
        
        markup.add(*btns)
        bot.delete_message(message.chat.id, wait_msg.message_id)
        bot.send_message(message.chat.id, response_text, reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        print(f"Ошибка поиска: {e}")
        bot.edit_message_text("⚠️ Сервис временно перегружен. Попробуй нажать кнопку еще раз через 5 секунд.", message.chat.id, wait_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def handle_download(call):
    index = int(call.data.split('_')[1])
    user_id = call.message.chat.id
    
    if user_id not in user_cache:
        bot.answer_callback_query(call.id, "❌ Результаты устарели, соверши поиск заново.")
        return

    track = user_cache[user_id][index]
    bot.answer_callback_query(call.id, "🚀 Начинаю загрузку...")
    bot.send_chat_action(user_id, 'upload_document')
    
    # Формируем имя файла
    file_path = f"track_{track.id}.mp3"
    
    try:
        api = SoundcloudAPI()
        with open(file_path, 'wb+') as fp:
            track.write_mp3_to(fp)
        
        with open(file_path, 'rb') as audio:
            bot.send_audio(
                user_id, 
                audio, 
                title=track.title, 
                performer=track.artist,
                caption=f"✅ Трек готов! Приятного прослушивания."
            )
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        bot.send_message(user_id, "❌ Не удалось скачать этот трек. Попробуй другой из списка.")
    finally:
        # Удаляем файл с сервера в любом случае
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    print("Бот успешно запущен и готов к работе!")
    bot.polling(none_stop=True)
