# универсальные методы бота (отправка сообщений, ответ на callback и т.д.)
import json
from datetime import datetime
from httpx import AsyncClient
from app.config import settings


async def bot_send_message(client: AsyncClient, chat_id: int, text: str, kb: list | None = None):
    send_data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if kb:
        send_data["reply_markup"] = {"inline_keyboard": kb}
    await client.post(f"{settings.get_tg_api_url()}/sendMessage", json=send_data)


async def call_answer(client: AsyncClient, callback_query_id: int, text: str):
    await client.post(f"{settings.get_tg_api_url()}/answerCallbackQuery", json={
        "callback_query_id": callback_query_id,
        "text": text
    })


def get_greeting_text(first_name: str):
    return f"""
🏥 <b>Добро пожаловать в бот пространства "Море Идей"!</b>
Здравствуйте, <b>{first_name}</b>! 👋
Мы рады приветствовать вас в нашей цифровой системе записи на консультации. Здесь вы сможете:
✅ Записаться на консультацию к специалисту по вопросм бизнеса
🗓 Управлять своими записями
ℹ️ Получать информацию о наших услугах

<i>Море Идей - Ваш проводник в море бизнеса!</i>
Чтобы начать, выберите нужный пункт меню ниже 👇
"""


def get_about_text():
    return """
🏥 <b>О пространстве "Море Идей"</b>
Мы - сообщество предпринимателей и бизнес-тренеров, предоставляющая качественные услуги по консультации бизнеса с 2016 года.

<b>Наши преимущества:</b>

✅ Команда опытных наставников и действующих предпринимателей
🏆 Лучшие методики диагностики и прокачки бизнеса
🕒 Удобный график работы: рабочие дни с 10:00 до 18:00
🏠 Комфортное расположение в центре города
💉 Широкий спектр консультационных услуг

<b>Мы консультируем по вопросам:</b>
• Диагностика бизнеса
• Бизнес модель
• Финансовая модель
• Маркетинг и Продажи
• Личный бренд руководителя
• Работа с персоналом
• Меры поддержки бизнеса

<i>Мы заботимся о вашем бизнесе вместе с Вами на каждом этапе!</i>

Чтобы записаться на консультацию или узнать больше о наших услугах, воспользуйтесь меню бота.
"""


def pluralize_appointments(count: int) -> str:
    if count == 1:
        return "консультация"
    elif 2 <= count <= 4:
        return "консультации"
    else:
        return "консультаций"


def get_booking_text(appointment_count):
    if appointment_count > 0:
        message_text = f"""
📅 <b>Ваши записи к специалистам</b>
У вас запланировано <b>{appointment_count}</b> {pluralize_appointments(appointment_count)}.

Чтобы просмотреть детали ваших записей, нажмите кнопку "Просмотреть записи" ниже.
"""
    else:
        message_text = """
📅 <b>Ваши записи к специалистам</b>

В настоящее время у вас нет запланированных встреч.

Чтобы записаться к специалисту, воспользуйтесь кнопкой "Записаться на консультацию" в главном меню.
"""
    return message_text


def format_appointment(appointment, start_text="🗓 <b>Запись на консультацию</b>"):
    appointment_date = datetime.strptime(appointment['day_booking'], '%Y-%m-%d').strftime('%d.%m.%Y')
    return f"""
{start_text}

📅 Дата: {appointment_date}
🕒 Время: {appointment['time_booking']}
👨‍⚕️ Направление: {appointment['doctor_full_name']}
🏥 Специализация: {appointment['special']}

ℹ️ Номер записи: {appointment['id']}

Пожалуйста, приходите за 10-15 минут до назначенного времени.
"""
