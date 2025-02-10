from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dao import SpecializationDAO, DoctorDAO, BookingDAO, UserDAO
from app.api.schemas import SpecIDModel, BookingRequest
from app.dao.session_maker_fast_api import db
from app.tg_bot.scheduler_task import schedule_appointment_notification
import pytz

MOSCOW_TZ = pytz.timezone("Europe/Moscow")
router = APIRouter()


@router.get("/specialists")
async def get_specialists(session: AsyncSession = Depends(db.get_db)):
    return await SpecializationDAO.find_all(session=session)


@router.get("/doctors/{spec_id}")
async def get_doctors_spec(spec_id: int, session: AsyncSession = Depends(db.get_db)):
    return await DoctorDAO.find_all(session=session,
                                    filters=SpecIDModel(specialization_id=spec_id))


@router.get("/doctor/{doctor_id}")
async def get_doctor_by_id(doctor_id: int, session: AsyncSession = Depends(db.get_db)):
    return await DoctorDAO.find_one_or_none_by_id(session=session, data_id=doctor_id)


@router.get("/booking/available-slots/{doctor_id}")
async def get_available_slots(
        doctor_id: int,
        start_date: date,
        session: AsyncSession = Depends(db.get_db)
):
    return await BookingDAO.get_available_slots(session=session, doctor_id=doctor_id,
                                                start_date=start_date)


@router.post("/book")
async def book_appointment_and_schedule_notifications(
        booking_request: BookingRequest, session: AsyncSession = Depends(db.get_db_with_commit)
):
    """
    Эндпоинт для бронирования записи и планирования уведомлений.
    """
    try:
        # Получение user_id по Telegram ID
        user_id = await UserDAO.get_user_id(session=session, telegram_id=booking_request.user_id)

        # Создание брони в базе данных
        appointment = await BookingDAO.book_appointment(
            session=session,
            doctor_id=booking_request.doctor_id,
            user_id=user_id,
            day_booking=booking_request.day_booking,
            time_booking=booking_request.time_booking
        )
        doctor_info = await DoctorDAO.find_one_or_none_by_id(session=session, data_id=booking_request.doctor_id)

        # Формирование объекта appointment для уведомлений
        appointment_details = {
            'id': appointment.id,
            'day_booking': appointment.day_booking.strftime("%Y-%m-%d"),
            'time_booking': appointment.time_booking.strftime("%H:%M"),
            'special': doctor_info.special,
            'doctor_full_name': f'{doctor_info.first_name} {doctor_info.last_name} {doctor_info.patronymic}'
        }

        # Расчет времени напоминаний
        booking_time_str = f"{appointment_details['day_booking']} {appointment_details['time_booking']}"
        booking_time = datetime.strptime(booking_time_str, "%Y-%m-%d %H:%M").replace(tzinfo=MOSCOW_TZ)
        now = datetime.now(MOSCOW_TZ)
        notification_times = []

        # Напоминание 1: Сразу
        await schedule_appointment_notification(
            user_tg_id=booking_request.user_id,
            appointment=appointment_details,
            notification_time=now,
            reminder_label="immediate"
        )
        notification_times.append(now)

        # Напоминание 2: За сутки
        time_24h = booking_time - timedelta(hours=24)
        if time_24h > now:
            await schedule_appointment_notification(
                user_tg_id=booking_request.user_id,
                appointment=appointment_details,
                notification_time=time_24h,
                reminder_label="24h"
            )
            notification_times.append(time_24h)

        # Напоминание 3: За 6 часов
        time_6h = booking_time - timedelta(hours=6)
        if time_6h > now:
            await schedule_appointment_notification(
                user_tg_id=booking_request.user_id,
                appointment=appointment_details,
                notification_time=time_6h,
                reminder_label="6h"
            )
            notification_times.append(time_6h)

        # Напоминание 4: За 30 минут
        time_30min = booking_time - timedelta(minutes=30)
        if time_30min > now:
            await schedule_appointment_notification(
                user_tg_id=booking_request.user_id,
                appointment=appointment_details,
                notification_time=time_30min,
                reminder_label="30min"
            )
            notification_times.append(time_30min)

        # Форматирование времени уведомлений для ответа
        notification_times_formatted = [time.strftime("%Y-%m-%d %H:%M:%S") for time in notification_times]

        return {
            "status": "SUCCESS",
            "message": "Запись успешно создана и напоминания запланированы!",
            "appointment": appointment_details,
            "notification_times": notification_times_formatted
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in book_appointment_and_schedule_notifications endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Ошибка при создании брони и планировании уведомлений"
        )

