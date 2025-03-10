# клавиатуры бота

from app.config import settings

main_kb = [
    [{"text": "📅 Мои записи", "callback_data": "booking"}],
    [{"text": "🔖 Записаться на консультацию", "web_app": {"url": f"{settings.FRONT_SITE}"}}],
    [{"text": "ℹ️ О нас", "callback_data": "about_us"}]
]

back_kb = [
    [{"text": "🏠 Главное меню", "callback_data": "home"}],
    [{"text": "🔖 Записаться на консультацию", "web_app": {"url": f"{settings.FRONT_SITE}"}}]
]

def generate_kb_profile(user_db_id: int, count_booking: int):
    kb_profile = [
        [{"text": "🏠 Главное меню", "callback_data": "home"}],
        [{"text": "🔖 Записаться н консультацию", "web_app": {"url": f"{settings.FRONT_SITE}"}}]
    ]
    if count_booking > 0:
        kb_profile.append([{"text": f"🔒 Мои записи ({count_booking})", "callback_data": f"my_booking_{user_db_id}"}])
    return kb_profile