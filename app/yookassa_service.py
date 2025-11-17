import uuid
import asyncio
import aiohttp
import base64
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Payment, User
from app.config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY


class YookassaService:
    def __init__(self):
        self.shop_id = YOOKASSA_SHOP_ID
        self.secret_key = YOOKASSA_SECRET_KEY
        self.base_url = "https://api.yookassa.ru/v3"
        self.auth = base64.b64encode(f"{self.shop_id}:{self.secret_key}".encode()).decode()

    async def create_sbp_payment(self, amount: float, description: str, payment_id: int, user_tg_id: int):
        """ЗАГЛУШКА: Создание тестового платежа через СБП"""
        print(f"🔧 ЗАГЛУШКА: Создание платежа {amount}₽ для пользователя {user_tg_id}")

        # Возвращаем тестовые данные
        test_payment_id = f"test_payment_{payment_id}_{uuid.uuid4().hex[:8]}"

        return {
            'id': test_payment_id,
            'confirmation_url': 'https://example.com/payment',
            'qr_url': 'https://example.com/qr',
            'amount': amount,
            'description': description,
            'status': 'pending'
        }

    async def check_payment_status(self, payment_id: str):
        """ЗАГЛУШКА: Проверка статуса платежа - всегда успешно"""
        print(f"🔧 ЗАГЛУШКА: Проверка платежа {payment_id} - ВСЕГДА УСПЕШНО")

        # Всегда возвращаем успешный платеж
        return {
            'id': payment_id,
            'status': 'succeeded',
            'paid': True,
            'amount': {
                'value': '49.99',
                'currency': 'RUB'
            }
        }

    def get_payment_description(self, payment_type: str):
        """Получить описание платежа"""
        descriptions = {
            "reveal": "Раскрытие анонимного отправителя",
            "day_sub": "Подписка на 1 день - Анонимный чат",
            "month_sub": "Подписка на 30 дней - Анонимный чат"
        }
        return descriptions.get(payment_type, "Услуга анонимного чата")


yookassa_service = YookassaService()
