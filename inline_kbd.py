from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

admin_choices = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Отправлять сообщеня 🟢', callback_data='start_messages')],
    [InlineKeyboardButton(text='Остановить сообщения 🔴', callback_data='stop_messages')],
    [InlineKeyboardButton(text='Скачать keywords.txt 📂', callback_data='keywords_data')],
    [InlineKeyboardButton(text='Импортировать новый файл📂', callback_data='import_keywords_data'),],
    [InlineKeyboardButton(text='Добавить слово ➕', callback_data='add_one_keyword')],

])

