# задачи по расписанию

from loguru import logger
from app.async_client import http_client_manager
from app.config import scheduler
from app.tg_bot.kbs import back_kb, main_kb, generate_kb_profile
from app.tg_bot.methods import bot_send_message, format_appointment
from datetime import datetime

async def send_user_noti(user_tg_id: int, appointment: dict):
    client = http_client_manager.get_client()
    text = format_appointment(appointment, start_text="❗ Напоминаем, что у вас назначена запись на консультацию ❗")
    try:
        await bot_send_message(client=client, chat_id=user_tg_id, text=text, kb=back_kb)
    except Exception as e:
        logger.error(e)


async def schedule_appointment_notification(user_tg_id: int, appointment: dict, notification_time: datetime,
                                            reminder_label: str):
    """
    Планирует напоминание с уникальным job_id для каждого случая.

    :param user_tg_id: ID пользователя Telegram
    :param appointment: Данные о записи
    :param notification_time: Время напоминания
    :param reminder_label: Уникальный идентификатор напоминания (например, 'immediate', '24h', '6h', '30min')
    """
    # Уникальный идентификатор задания
    job_id = f"notification_{user_tg_id}_{appointment['id']}_{reminder_label}"

    # Планируем задание
    scheduler.add_job(
        send_user_noti,
        'date',
        run_date=notification_time,
        args=[user_tg_id, appointment],
        id=job_id,
        replace_existing=True
    )


