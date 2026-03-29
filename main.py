import telebot
from telebot import types
import yt_dlp
import os

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки поиска (имитация запросов ВК чартов)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch15',
    'extract_flat': False,
}

user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    # Описание бота как ты просил
    about = (
        "🎵 **VK Music Search | Поиск музыки**\n\n"
        "Добро пожаловать! Здесь ты можешь найти любой трек из чартов ВК и СНГ.\n"
        "Просто введи название песни или имя артиста."
    )
    bot.send_message(message.chat.id, about, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ Напиши название (например: *Три дня дождя*):", parse_mode='Markdown')
    elif message.text == "🚀 Популярное":
        search_music(message, "ВК Чарты 2026 топ 100")
    elif message.text == "✨ Новинки":
        search_music(message, "Новинки музыки 2026 СНГ")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        search_music(message, message.text)

def search_music(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу треки в базе ВК...*", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Ищем 15 результатов для гибкости
            info = ydl.extract_info(f"ytsearch15:{query}", download=False)
            tracks = info['entries']
            
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks):
            title = track.get('title', 'Неизвестно')
            # Очистка названия от мусора (Official Video и т.д.)
            clean_title = title.split('(')[0].split('[')[0].strip()
            # Кнопка: Артист — Название
            display_text = (clean_title[:45] + '..') if len(clean_title) > 45 else clean_title
            markup.add(types.InlineKeyboardButton(text=display_text, callback_data=f"vk_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 Результаты по запросу: *{query}*", 
                         reply_markup=markup, parse_mode='Markdown')
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('vk_'))
def send_track(call):
    idx = int(call.data.split('_')[1])
    track_info = user_results[call.message.chat.id][idx]
    
    # Прямая ссылка на аудиопоток (полная версия)
    url = track_info['url']
    full_title = track_info.get('title', 'Music')
    
    # Пытаемся разделить на Артиста и Название для плеера
    if " — " in full_title:
        performer, title = full_title.split(" — ", 1)
    elif " - " in full_title:
        performer, title = full_title.split(" - ", 1)
    else:
        performer, title = "VK Music", full_title

    bot.answer_callback_query(call.id, "📥 Отправляю полную версию...")
    
    # Отправляем аудио (будет отображаться в плеере с кнопкой Play)
    bot.send_audio(
        call.message.chat.id, 
        url, 
        title=title.strip(), 
        performer=performer.strip(),
        caption=f"🎧 **{performer.strip()} — {title.strip()}**",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
