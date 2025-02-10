# функции бота (реагирование на команду /start и т.д.)

from httpx import AsyncClient
from app.api.dao import UserDAO, BookingDAO
from app.api.schemas import TelegramIDModel, UserModel
from app.tg_bot.kbs import back_kb, main_kb, generate_kb_profile
from app.tg_bot.methods import call_answer, bot_send_message, get_greeting_text, get_about_text, get_booking_text, format_appointment


async def cmd_start(client: AsyncClient, session, user_info):
    user_in_db = await UserDAO.find_one_or_none(session=session, filters=TelegramIDModel(telegram_id=user_info["id"]))

    if not user_in_db:
        # Добавляем нового пользователя
        values = UserModel(
            telegram_id=user_info["id"],
            username=user_info.get("username"),
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name")
        )
        await UserDAO.add(session=session, values=values)

    greeting_message = get_greeting_text(user_info.get("first_name"))
    await bot_send_message(client, user_info["id"], greeting_message, main_kb)

async def handler_back_home(client: AsyncClient, callback_query_id: int, chat_id: int):
    await call_answer(client, callback_query_id, "Главное меню")
    await bot_send_message(client, chat_id, "Вы на главной странице!", main_kb)


async def handler_about_us(client: AsyncClient, callback_query_id: int, chat_id: int):
    await call_answer(client, callback_query_id, "О нас")
    about_us_text = get_about_text()
    await bot_send_message(client, chat_id, about_us_text, back_kb)

async def handler_my_appointments(client: AsyncClient, callback_query_id: int, chat_id: int, session):
    await call_answer(client, callback_query_id, "Ваши записи к врачам")
    db_user_id = await UserDAO.get_user_id(session=session, telegram_id=chat_id)
    appointment_count = await BookingDAO.count_user_booking(session=session, user_id=db_user_id)
    message_text = get_booking_text(appointment_count)
    keyboard = generate_kb_profile(db_user_id, appointment_count)
    await bot_send_message(client, chat_id, message_text, kb=keyboard)


async def handler_my_appointments_all(client: AsyncClient,
                                      callback_query_id: int,
                                      chat_id: int,
                                      user_db_id: int,
                                      session):
    await call_answer(client, callback_query_id, "Ваши записи к врачам (подробно)")
    appointments = await BookingDAO.get_user_bookings_with_doctor_info(session=session, user_id=user_db_id)

    for appointment in appointments:
        await bot_send_message(client, chat_id, format_appointment(appointment))

    await bot_send_message(client, chat_id, "Это все ваши текущие записи.", main_kb)



