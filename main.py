import telebot
from telebot import types
import requests

# Твой токен
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
bot = telebot.TeleBot(TG_TOKEN)

user_results = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Популярное"), types.KeyboardButton("✨ Новинки"))
    markup.add(types.KeyboardButton("🔍 Поиск музыки"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    # Приветствие внутри бота
    welcome_text = (
        "✨ **VK Music Bot | Поиск музыки** ✨\n\n"
        "Рад тебя видеть! Я помогу тебе найти и послушать любой трек.\n\n"
        "🔹 **Как искать?**\n"
        "Просто напиши имя артиста (например: `Три дня дождя`) или название песни.\n\n"
        "🔥 **Разделы:**\n"
        "• `Популярное` — топ-чарты СНГ прямо сейчас.\n"
        "• `Новинки` — самые свежие релизы 2026 года.\n\n"
        "👇 **Выбери действие в меню:**"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"])
def menu_logic(message):
    if message.text == "🔍 Поиск музыки":
        bot.send_message(message.chat.id, "⌨️ **Напиши название трека или артиста:**", parse_mode='Markdown')
    elif message.text == "🚀 Популярное":
        fast_search(message, "Top Hits Russia 2026")
    elif message.text == "✨ Новинки":
        fast_search(message, "New Russian Music 2026")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    # Если пользователь просто пишет текст — это поиск
    if message.text not in ["🚀 Популярное", "✨ Новинки", "🔍 Поиск музыки"]:
        fast_search(message, message.text)

def fast_search(message, query):
    wait = bot.send_message(message.chat.id, "🔎 *Ищу варианты в базе...*", parse_mode='Markdown')
    try:
        # Поиск 20 вариантов через базу iTunes (быстро и точно)
        url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=25&country=ru"
        res = requests.get(url).json()
        tracks = res.get('results', [])

        if not tracks:
            bot.edit_message_text("❌ По твоему запросу ничего не найдено.", message.chat.id, wait.message_id)
            return

        user_results[message.chat.id] = tracks
        markup = types.InlineKeyboardMarkup()
        
        for i, track in enumerate(tracks):
            artist = track.get('artistName', 'Артист')
            title = track.get('trackName', 'Трек')
            btn_text = f"{artist} — {title}"
            
            # Обрезаем очень длинные названия для кнопок
            short_text = (btn_text[:40] + '..') if len(btn_text) > 40 else btn_text
            markup.add(types.InlineKeyboardButton(text=short_text, callback_data=f"aud_{i}"))
        
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, f"🎶 **Результаты по запросу:** _{query}_", 
                         reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка. Попробуй еще раз.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('aud_'))
def send_audio(call):
    idx = int(call.data.split('_')[1])
    if call.message.chat.id not in user_results:
        bot.answer_callback_query(call.id, "Поиск устарел, введи название заново.")
        return

    track = user_results[call.message.chat.id][idx]
    artist = track.get('artistName')
    title = track.get('trackName')
    audio_url = track.get('previewUrl')

    bot.answer_callback_query(call.id, f"📥 Загружаю: {title}")
    
    # Отправка в плеер с корректными данными
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
