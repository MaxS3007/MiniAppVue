from datetime import date, timedelta, datetime, time, timezone
from typing import List
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select, and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.dao.base import BaseDAO
from app.dao.models import User, Specialization, Doctor, Booking


class SpecializationDAO(BaseDAO[Specialization]):
    model = Specialization


class DoctorDAO(BaseDAO[Specialization]):
    model = Doctor


class UserDAO(BaseDAO[User]):
    model = User

    @classmethod
    async def get_user_id(cls, session: AsyncSession, telegram_id: int) -> int | None:
        query = select(cls.model.id).filter_by(telegram_id=telegram_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


class BookingDAO(BaseDAO[Booking]):
    model = Booking

    @classmethod
    async def count_user_booking(cls, session: AsyncSession, user_id: int) -> int:
        query = select(func.count()).where(cls.model.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one()

    @classmethod
    async def get_user_bookings_with_doctor_info(cls, session: AsyncSession, user_id: int):
        query = (
            select(cls.model)
            .options(joinedload(cls.model.doctor))
            .where(cls.model.user_id == user_id)
            .order_by(cls.model.day_booking, cls.model.time_booking)
        )
        result = await session.execute(query)
        result_draft = result.unique().scalars().all()
        data_list = []
        for info in result_draft:
            data_list.append({
                "id": info.id,
                "day_booking": info.day_booking.strftime("%Y-%m-%d"),
                "time_booking": info.time_booking.strftime("%H:%M"),
                "special": info.doctor.special,
                "doctor_full_name": f"{info.doctor.first_name} {info.doctor.last_name} {info.doctor.patronymic}",
            })
        return data_list

    @classmethod
    def generate_working_hours(cls, start_hour=10, end_hour=17, step_minutes=30) -> List[str]:
        """Генерирует список рабочих часов с заданным интервалом"""
        working_hours = []
        current_time = datetime.strptime(f"{start_hour}:00", "%H:%M")
        end_time = datetime.strptime(f"{end_hour}:00", "%H:%M")

        while current_time <= end_time:
            working_hours.append(current_time.strftime("%H:%M"))
            current_time += timedelta(minutes=step_minutes)

        return working_hours[:-1]

    @classmethod
    async def get_available_slots(
            cls,
            session: AsyncSession,
            doctor_id: int,
            start_date: date
    ) -> dict[str, int | list[dict[str, str | int | list[str]]]]:
        """
        Получает доступные слоты для записи к врачу на неделю вперед, с учетом требований.

        Args:
            session: AsyncSession - сессия базы данных
            doctor_id: int - ID врача
            start_date: date - дата заказа

        Returns:
            List[Dict[str, Union[str, List[str], int]]] - список дней с доступными слотами
        """
        try:
            # Сопоставляем дату с началом недели (понедельник)
            start_of_week = start_date - timedelta(days=start_date.weekday())
            end_of_week = start_of_week + timedelta(days=5)

            # Получаем существующие брони
            query = select(cls.model).where(
                and_(
                    cls.model.doctor_id == doctor_id,
                    cls.model.day_booking >= start_of_week,
                    cls.model.day_booking <= end_of_week
                )
            )
            result = await session.execute(query)
            existing_bookings = result.scalars().all()

            # Получаем список рабочих часов
            working_hours = cls.generate_working_hours()

            # Создаем множество занятых слотов
            booked_slots = {
                (
                    booking.day_booking.isoformat(),
                    booking.time_booking.strftime("%H:%M")
                )
                for booking in existing_bookings
            }

            # Названия дней недели на русском
            week_days_rus = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]

            # Результат
            available_slots = []

            for day_offset in range(6):
                current_date = start_of_week + timedelta(days=day_offset)
                current_date_str = current_date.isoformat()
                day_name_rus = week_days_rus[day_offset]

                # Если текущая дата меньше сегодняшней, слоты пустые
                day_slots = []
                if current_date > datetime.now().date():
                    for time_str in working_hours:
                        is_available = (current_date_str, time_str) not in booked_slots

                        if current_date == datetime.now().date():
                            slot_time = datetime.strptime(time_str, "%H:%M").time()
                            if slot_time <= datetime.now(timezone.utc).time():
                                is_available = False

                        if is_available:
                            day_slots.append(time_str)

                # Добавляем в результат
                available_slots.append({
                    "day": day_name_rus,
                    "date": current_date_str,
                    "slots": day_slots,
                    "total_slots": len(day_slots)
                })

            # Фильтруем дни для переданной даты
            filter_data = [
                day for day in available_slots if
                start_of_week <= datetime.fromisoformat(day["date"]).date() <= end_of_week
            ]

            return {"days": filter_data,
                    "total_week_slots": sum(day["total_slots"] for day in filter_data)}

        except Exception as e:
            # Логирование ошибки
            logger.error(f"Error in get_available_slots: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error while getting available slots"
            )

    @classmethod
    async def book_appointment(
            cls,
            session: AsyncSession,
            doctor_id: int,
            user_id: int,
            day_booking: date,
            time_booking: time
    ) -> Booking:
        """
        Метод для бронирования записи.

        Args:
            session: AsyncSession - сессия базы данных
            doctor_id: int - ID врача
            user_id: int - ID пользователя
            day_booking: date - дата брони
            time_booking: time - время брони

        Returns:
            Booking - созданная запись
        """
        try:
            today = date.today()
            logger.info(f"today: {today}, day_booking: {day_booking}")
            if day_booking < date.today():
                raise HTTPException(
                    status_code=400,
                    detail="Дата бронирования не может быть меньше сегодняшней даты"
                )

            # Проверяем, что время бронирования в правильном диапазоне и с шагом в 30 минут
            if not (time(8, 0) <= time_booking <= time(19, 30)):
                raise HTTPException(
                    status_code=400,
                    detail="Время бронирования должно быть между 08:00 и 19:30"
                )
            logger.info(f"МИНУТЫ: {time_booking.minute}")
            if time_booking.minute not in [0, 30]:
                raise HTTPException(
                    status_code=400,
                    detail="Время бронирования должно быть на целый час или на 30 минут"
                )

            # Проверяем, что слот не занят
            query = select(cls.model).where(
                and_(
                    cls.model.doctor_id == doctor_id,
                    cls.model.day_booking == day_booking,
                    cls.model.time_booking == time_booking
                )
            )
            result = await session.execute(query)
            existing_booking = result.scalar_one_or_none()

            if existing_booking:
                raise HTTPException(
                    status_code=400,
                    detail="Слот уже забронирован"
                )

            # Создаем новую бронь
            new_booking = cls.model(
                doctor_id=doctor_id,
                user_id=user_id,
                day_booking=day_booking,
                time_booking=time_booking,
                booking_status="confirmed",  # Статус брони
                created_at=datetime.now(timezone.utc)  # Обновлено
            )
            session.add(new_booking)
            await session.flush()
            return new_booking

        except IntegrityError as e:
            logger.error(f"IntegrityError in book_appointment: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail="Ошибка базы данных при создании брони"
            )
