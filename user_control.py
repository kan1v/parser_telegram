# Временное хранилище статуса отправки сообщений
user_message_status = {}

def is_user_active(user_id: int) -> bool:
    return user_message_status.get(user_id, True)  # По умолчанию True

def set_user_status(user_id: int, status: bool):
    user_message_status[user_id] = status
