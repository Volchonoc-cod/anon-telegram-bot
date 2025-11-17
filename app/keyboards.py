from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


# Главное меню
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔗 Моя ссылка")],
            [KeyboardButton(text="🔄 Пересоздать ссылку"), KeyboardButton(text="👁️ Раскрыть отправителя")],
            [KeyboardButton(text="💰 Платные функции")]
        ],
        resize_keyboard=True
    )


# Универсальная клавиатура для всех сообщений
def message_actions_keyboard(message_id: int, can_reveal: bool = True):
    buttons = [
        [
            InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{message_id}"),
            InlineKeyboardButton(text="🚫 Пожаловаться", callback_data=f"report_{message_id}")
        ]
    ]

    if can_reveal:
        buttons.append([
            InlineKeyboardButton(text="👁️ Раскрыть отправителя", callback_data=f"reveal_{message_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="💰 Купить раскрытие", callback_data="buy_reveal")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Подтверждение пересоздания ссылки
def recreate_link_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, пересоздать", callback_data="recreate_link_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="recreate_link_cancel")]
        ]
    )


# Меню платных функций
def premium_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👁️ Раскрыть 1 сообщение - 49.99₽", callback_data="buy_reveal")],
            [InlineKeyboardButton(text="📅 Подписка на 1 день - 139.99₽", callback_data="buy_day_sub")],
            [InlineKeyboardButton(text="📆 Подписка на месяц - 399.99₽", callback_data="buy_month_sub")],
            [InlineKeyboardButton(text="📊 Мой статус", callback_data="my_status")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ]
    )


# Клавиатура для оплаты через СБП (ЗАГЛУШКА - упрощенная)
def sbp_payment_keyboard(confirmation_url: str = None, qr_url: str = None):
    keyboard = []

    if confirmation_url:
        keyboard.append([InlineKeyboardButton(text="🔗 Перейти к оплате", url=confirmation_url)])

    if qr_url:
        keyboard.append([InlineKeyboardButton(text="📱 QR-код для СБП", url=qr_url)])

    # ЗАГЛУШКА: Упрощенная клавиатура
    keyboard.extend([
        [InlineKeyboardButton(text="✅ Тестовая оплата", callback_data="check_payment")],
        [InlineKeyboardButton(text="❌ Отменить оплату", callback_data="cancel_payment")]
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура для проверки платежа
def payment_check_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_payment")]
        ]
    )