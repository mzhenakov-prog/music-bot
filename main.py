import telebot
from telebot import types
import yt_dlp

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки для получения музыки в формате аудио-плеера
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch10',
    # Ограничение по времени, чтобы не лезла "дичь" по 2 часа
    'match_filter': yt_dlp.utils.match_filter_func("duration < 400"), 
}

user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔥 ТОП Чарты"), types.KeyboardButton("🆕 Новинки недели"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "🎵 **Музыкальный Плеер**\n\nВыбери раздел или просто напиши название трека. Я пришлю его в обычном формате для прослушивания в Telegram!", 
        reply_markup=main_menu(), 
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text in ["🔥 ТОП Чарты", "🆕 Новинки недели", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ **Введите название трека или артиста:**", parse_mode='Markdown')
    elif message.text == "🔥 ТОП Чарты":
        search_engine(message, "Top 50 Russia Hits 2026")
    elif message.text == "🆕 Новинки недели":
        search_engine(message, "New releases 2026 CIS music")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text not in ["🔥 ТОП Чарты", "🆕 Новинки недели", "🔍 Поиск музыки"]:
        search_engine(message, message.text)

def search_engine(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу треки...*")
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Принудительно ищем "audio", чтобы не было видео-клипов
            info = ydl.extract_info(f"{query} official audio", download=False)
            tracks = [e for e in info['entries'] if e]
            
        if not tracks:
            bot.edit_message_text("❌ Треки не найдены. Попробуй другой запрос.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks[:10]):
            title = track.get('title', 'Track')
            # Чистим название для кнопки
            clean_btn = title.split('|')[0].split('(')[0].strip()[:40]
            markup.add(types.InlineKeyboardButton(text=f"▶️ {clean_btn}", callback_data=f"tr_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 Найдено по запросу: *{query}*", reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tr_'))
def send_music(call):
    idx = int(call.data.split('_')[1])
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "❌ Поиск устарел.")
        return

    track = user_results[call.message.chat.id][idx]
    bot.answer_callback_query(call.id, "📥 Загружаю в плеер...")
    
    url = track['url']
    full_title = track.get('title', 'Music')
    
    # Разделяем на Исполнитель - Название для нормального вида в плеере
    if " - " in full_title:
        performer, title = full_title.split(" - ", 1)
    elif " — " in full_title:
        performer, title = full_title.split(" — ", 1)
    else:
        performer, title = "VK Music", full_title

    # Убираем мусор из названия
    clean_title = title.split('(')[0].split('[')[0].strip()

    # ОТПРАВКА В ФОРМАТЕ ПЛЕЕРА
    bot.send_audio(
        call.message.chat.id, 
        url, 
        title=clean_title, 
        performer=performer.strip(),
        caption=f"✅ {performer.strip()} — {clean_title}",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
