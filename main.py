import telebot
from telebot import types
import yt_dlp

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки поиска: ТОЛЬКО короткие треки (до 6 мин)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch10',
    'match_filter': yt_dlp.utils.match_filter_func("duration < 360"),
}

user_results = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎶 **VK Music Search**\n\nНапиши название песни или артиста. Я найду только полные треки без длинных миксов!", parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def handle_text(message):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу треки...*", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Добавляем "audio", чтобы поиск был точнее
            info = ydl.extract_info(f"{message.text} audio", download=False)
            tracks = [entry for entry in info['entries'] if entry]
            
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено (длинные миксы скрыты).", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks[:10]):
            title = track.get('title', 'Unknown').split('|')[0].split('(')[0].strip()[:45]
            markup.add(types.InlineKeyboardButton(text=title, callback_data=f"tr_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 Результаты для: *{message.text}*", reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tr_'))
def send_music(call):
    idx = int(call.data.split('_')[1])
    # Проверяем, есть ли данные в памяти
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "❌ Поиск устарел, введи название снова.")
        return

    track = user_results[call.message.chat.id][idx]
    bot.answer_callback_query(call.id, "📥 Отправляю трек...")
    
    url = track['url']
    full_title = track.get('title', 'Music')
    
    # Исправленная логика разделения (без SyntaxError)
    if " - " in full_title:
        performer, title = full_title.split(" - ", 1)
    elif " — " in full_title:
        performer, title = full_title.split(" — ", 1)
    else:
        performer, title = "VK Music", full_title

    clean_title = title.split('(')[0].split('[')[0].strip()

    bot.send_audio(
        call.message.chat.id, 
        url, 
        title=clean_title, 
        performer=performer.strip(),
        caption=f"✅ **{performer.strip()} — {clean_title}**",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)
