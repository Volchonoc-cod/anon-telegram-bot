from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime

from app.database import get_db
from app.models import User, Payment
from app.keyboards import premium_menu, sbp_payment_keyboard, payment_check_keyboard, main_menu
from app.payment_service import payment_service
from app.yookassa_service import yookassa_service
from app.config import ADMIN_IDS
from app.backup_service import backup_service

router = Router()


class PaymentStates(StatesGroup):
    waiting_payment = State()


# Команда для платных функций
@router.message(Command("premium"))
@router.message(F.text == "💰 Платные функции")
async def show_premium_menu(message: types.Message):
    db = next(get_db())
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        status_text = "🔒 Бесплатный аккаунт"
        if payment_service.is_user_premium(user):
            status_text = f"⭐ Премиум до {user.premium_until.strftime('%d.%m.%Y %H:%M')}"

        text = (
            f"💰 <b>Платные функции</b>\n\n"
            f"📊 <b>Ваш статус:</b> {status_text}\n"
            f"👁️ <b>Доступные раскрытия:</b> {user.available_reveals}\n\n"
            f"<b>Доступные покупки:</b>\n"
            f"• 👁️ Раскрыть 1 анонимное сообщение - 49.99₽\n"
            f"• 📅 Подписка на 1 день - 139.99₽\n"
            f"• 📆 Подписка на месяц - 399.99₽\n\n"
            f"<b>Оплата через СБП:</b>\n"
            f"✅ По номеру телефона или карты\n"
            f"✅ Мгновенное зачисление\n"
            f"✅ Без комиссии"
        )

        await message.answer(text, parse_mode="HTML", reply_markup=premium_menu())
    finally:
        db.close()


# Обработчики кнопок покупки
@router.callback_query(F.data == "buy_reveal")
async def buy_reveal_handler(callback: types.CallbackQuery, state: FSMContext):
    await process_payment(callback, state, "reveal")


@router.callback_query(F.data == "buy_day_sub")
async def buy_day_sub_handler(callback: types.CallbackQuery, state: FSMContext):
    await process_payment(callback, state, "day_sub")


@router.callback_query(F.data == "buy_month_sub")
async def buy_month_sub_handler(callback: types.CallbackQuery, state: FSMContext):
    await process_payment(callback, state, "month_sub")


async def process_payment(callback: types.CallbackQuery, state: FSMContext, payment_type: str):
    db = next(get_db())
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        # Создаем запись о платеже
        payment = payment_service.create_payment(db, user.id, payment_type)
        if not payment:
            await callback.answer("❌ Ошибка создания платежа")
            return

        # Создаем платеж в ЮKassa (ЗАГЛУШКА)
        payment_data = await payment_service.create_yookassa_payment(
            db, payment.id, callback.from_user.id, payment_type
        )

        if not payment_data:
            await callback.message.edit_text("❌ Ошибка при создании платежа. Попробуйте позже.")
            return

        # Сохраняем данные платежа в состоянии
        await state.update_data(
            payment_id=payment.id,
            yookassa_payment_id=payment_data['payment_id'],
            payment_type=payment_type,
            amount=payment_data['amount'],
            start_time=datetime.now().timestamp()
        )
        await state.set_state(PaymentStates.waiting_payment)

        # Отправляем инструкции по оплате (ЗАГЛУШКА - сразу завершаем платеж)
        amount = payment_data['amount']
        payment_type_text = {
            "reveal": "раскрытие 1 сообщения",
            "day_sub": "подписка на 1 день",
            "month_sub": "подписка на месяц"
        }[payment_type]

        # ЗАГЛУШКА: Сразу завершаем платеж
        success = payment_service.complete_payment(db, payment_data['payment_id'])

        if success:
            user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

            if payment_type == "reveal":
                message_text = "✅ Платеж получен! Теперь вы можете раскрыть 1 анонимное сообщение."
            elif payment_type == "day_sub":
                message_text = f"✅ Подписка активирована! Премиум до {user.premium_until.strftime('%d.%m.%Y %H:%M')}"
            else:  # month_sub
                message_text = f"✅ Подписка активирована! Премиум до {user.premium_until.strftime('%d.%m.%Y %H:%M')}"

            await callback.message.edit_text(message_text)
            await state.clear()

            # Уведомляем админов о успешном платеже
            await notify_admin_about_payment(
                callback.bot,
                amount,
                payment_type,
                callback.from_user.id
            )
        else:
            await callback.message.edit_text("❌ Ошибка при активации товара. Обратитесь в поддержку.")

        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в process_payment: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при создании платежа")
    finally:
        db.close()


# Ручная проверка оплаты
@router.callback_query(F.data == "check_payment")
async def check_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    await check_payment_status(callback, state, manual_check=True)


async def check_payment_status(callback: types.CallbackQuery, state: FSMContext, manual_check: bool = False):
    """Проверка статуса платежа (ЗАГЛУШКА - всегда успешно)"""
    user_data = await state.get_data()
    yookassa_payment_id = user_data.get('yookassa_payment_id')

    if not yookassa_payment_id:
        await callback.answer("❌ Данные платежа не найдены")
        return

    db = next(get_db())
    try:
        # ЗАГЛУШКА: Всегда успешный платеж
        success = payment_service.complete_payment(db, yookassa_payment_id)

        if success:
            user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
            payment_type = user_data.get('payment_type')

            if payment_type == "reveal":
                message_text = "✅ Платеж получен! Теперь вы можете раскрыть 1 анонимное сообщение."
            elif payment_type == "day_sub":
                message_text = f"✅ Подписка активирована! Премиум до {user.premium_until.strftime('%d.%m.%Y %H:%M')}"
            else:  # month_sub
                message_text = f"✅ Подписка активирована! Премиум до {user.premium_until.strftime('%d.%m.%Y %H:%M')}"

            await callback.message.edit_text(message_text)
            await state.clear()

            # Уведомляем админов о успешном платеже
            await notify_admin_about_payment(
                callback.bot,
                user_data.get('amount'),
                payment_type,
                callback.from_user.id
            )
        else:
            await callback.message.edit_text("❌ Ошибка при активации товара. Обратитесь в поддержку.")

    except Exception as e:
        print(f"❌ Ошибка проверки платежа: {e}")
        await callback.message.edit_text("❌ Ошибка при проверке платежа")
    finally:
        db.close()


async def notify_admin_about_payment(bot: Bot, amount: float, payment_type: str, user_tg_id: int):
    """Уведомление админов о успешном платеже"""
    payment_type_text = {
        "reveal": "Раскрытие сообщения",
        "day_sub": "Подписка на 1 день",
        "month_sub": "Подписка на месяц"
    }[payment_type]

    text = (
        f"💰 <b>Новый платеж!</b>\n\n"
        f"👤 Пользователь: {user_tg_id}\n"
        f"📦 Товар: {payment_type_text}\n"
        f"💵 Сумма: {amount:.2f}₽\n"
        f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as e:
            print(f"❌ Ошибка уведомления админа {admin_id}: {e}")


# Отмена платежа
@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Оплата отменена")
    await state.clear()
    await callback.answer()


# Просмотр статуса
@router.callback_query(F.data == "my_status")
async def show_my_status(callback: types.CallbackQuery):
    db = next(get_db())
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        status_text = "🔒 Бесплатный аккаунт"
        if payment_service.is_user_premium(user):
            status_text = f"⭐ Премиум (до {user.premium_until.strftime('%d.%m.%Y %H:%M')})"

        text = (
            f"📊 <b>Ваш статус</b>\n\n"
            f"👤 {user.first_name}\n"
            f"📱 Статус: {status_text}\n"
            f"👁️ Доступные раскрытия: {user.available_reveals}\n"
            f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}"
        )

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=premium_menu())
        await callback.answer()
    finally:
        db.close()


# Возврат в главное меню - ИСПРАВЛЕННЫЙ
@router.callback_query(F.data == "back_to_main")
async def back_to_main_from_premium(callback: types.CallbackQuery):
    # Используем answer вместо edit_text для Reply клавиатуры
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()
