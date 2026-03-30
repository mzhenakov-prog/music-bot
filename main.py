import telebot
from telebot import types

# ========== НАСТРОЙКИ ==========
TG_TOKEN = '8617337625:AAGFRB7FkLyu7FuomW9YD_C7vHlwad5wzqc'
CHANNEL_ID = '-1001888094511'
CHANNEL_URL = 'https://t.me/lyubimkatt'

bot = telebot.TeleBot(TG_TOKEN)

# ========== КНОПКИ ==========
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎵 Поиск музыки")
    markup.add("🆕 Новинки", "🔥 Топ 100")
    return markup

# ========== ПРОВЕРКА ПОДПИСКИ ==========
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# ========== СТАРТ ==========
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub"))
        bot.send_message(message.chat.id, "⚠️ *Доступ закрыт!*\n\nПодпишись на канал, чтобы слушать музыку.", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "🎵 *Муз-бот готов!*\n\nИспользуй кнопки внизу.", reply_markup=main_menu(), parse_mode='Markdown')

# ========== КНОПКА ПОИСКА ==========
@bot.message_handler(func=lambda msg: msg.text == "🎵 Поиск музыки")
def search_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎵 VK Music Bot", url="https://t.me/vkmusic_bot"))
    bot.send_message(message.chat.id, "🔍 *Поиск музыки через VK*\n\nНажми на кнопку, чтобы открыть бот VK Music:", reply_markup=markup, parse_mode='Markdown')

# ========== КНОПКА НОВИНКИ ==========
@bot.message_handler(func=lambda msg: msg.text == "🆕 Новинки")
def new_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎵 VK Music Bot", url="https://t.me/vkmusic_bot"))
    bot.send_message(message.chat.id, "🆕 *Новинки музыки*\n\nНажми на кнопку и найди свежие треки:", reply_markup=markup, parse_mode='Markdown')

# ========== КНОПКА ТОП 100 ==========
@bot.message_handler(func=lambda msg: msg.text == "🔥 Топ 100")
def top_button(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Сначала подпишись на канал!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎵 VK Music Bot", url="https://t.me/vkmusic_bot"))
    bot.send_message(message.chat.id, "🔥 *Топ 100 треков*\n\nНажми на кнопку и найди популярное:", reply_markup=markup, parse_mode='Markdown')

# ========== ПРОВЕРКА ПОДПИСКИ ==========
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_callback(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Подписка подтверждена!")
        bot.edit_message_text("🎉 Спасибо! Теперь ты можешь слушать музыку.", call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "🎵 *Муз-бот готов!*", reply_markup=main_menu(), parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписаны!", show_alert=True)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("🎵 Музыкальный бот запущен!")
    bot.polling(none_stop=True)
