import telebot
from telebot import types
import yt_dlp

TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

# Настройки для получения прямой ссылки на аудио
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch10',
    'match_filter': yt_dlp.utils.match_filter_func("duration < 420"), # До 7 минут
}

user_results = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    bot.send_message(message.chat.id, "🎶 **Муз-бот готов!**\nПришлю трек в плеер. Нажми кнопку или напиши название.", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск музыки")
def search_btn(message):
    bot.send_message(message.chat.id, "⌨️ **Напиши артиста и название песни:**")

@bot.message_handler(content_types=['text'])
def handle_search(message):
    if message.text == "🔍 Поиск музыки": return
    
    wait = bot.send_message(message.chat.id, "🔎 *Ищу...*")
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # Ищем конкретно аудио
            info = ydl.extract_info(f"{message.text} audio", download=False)
            tracks = [e for e in info['entries'] if e]
            
        if not tracks:
            bot.edit_message_text("❌ Ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        for i, track in enumerate(tracks[:8]):
            title = track.get('title', 'Track')[:45]
            markup.add(types.InlineKeyboardButton(text=f"▶️ {title}", callback_data=f"mus_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎵 Результаты по запросу: *{message.text}*", reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка поиска.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('mus_'))
def play_music(call):
    idx = int(call.data.split('_')[1])
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "❌ Поиск устарел.")
        return

    track = user_results[call.message.chat.id][idx]
    bot.answer_callback_query(call.id, "📥 Отправляю в плеер...")
    
    # Берем данные для плеера
    audio_url = track['url']
    full_title = track.get('title', 'Music')
    
    # Пытаемся красиво разделить Исполнителя и Название
    performer = "VK Music"
    title = full_title
    if " - " in full_title:
        performer, title = full_title.split(" - ", 1)
    
    try:
        # Шлем как аудио-ссылку (Телеграм сам подхватит в плеер)
        bot.send_audio(
            call.message.chat.id, 
            audio_url, 
            title=title.split('(')[0].strip(), 
            performer=performer.strip(),
            timeout=60
        )
    except:
        bot.send_message(call.message.chat.id, "❌ Не удалось загрузить этот трек в плеер. Попробуй другой из списка.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
