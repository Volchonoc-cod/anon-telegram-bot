import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User, Payment
from app.yookassa_service import yookassa_service


class PaymentService:
    PRICES = {
        'reveal': 49.99,  # 49.99 руб
        'day_sub': 139.99,  # 139.99 руб
        'month_sub': 399.99  # 399.99 руб
    }

    def create_payment(self, db: Session, user_id: int, payment_type: str):
        """Создание платежа"""
        if payment_type not in self.PRICES:
            return None

        payment = Payment(
            user_id=user_id,
            amount=int(self.PRICES[payment_type] * 100),  # в копейках
            payment_type=payment_type,
            status="pending",
            yookassa_payment_id=None
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    async def create_yookassa_payment(self, db: Session, payment_id: int, user_tg_id: int, payment_type: str):
        """Создание платежа в ЮKassa (с заглушкой)"""
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return None

        amount = self.PRICES[payment_type]
        description = yookassa_service.get_payment_description(payment_type)

        # ЗАГЛУШКА: Создаем тестовый платеж
        yookassa_data = await yookassa_service.create_sbp_payment(
            amount=amount,
            description=description,
            payment_id=payment_id,
            user_tg_id=user_tg_id
        )

        if yookassa_data:
            payment.yookassa_payment_id = yookassa_data['id']
            payment.status = "waiting"
            db.commit()

            return {
                'payment_id': yookassa_data['id'],
                'confirmation_url': yookassa_data.get('confirmation_url'),
                'qr_url': yookassa_data.get('qr_url'),
                'amount': amount
            }
        return None

    def complete_payment(self, db: Session, yookassa_payment_id: str):
        """Завершение платежа и применение benefits"""
        payment = db.query(Payment).filter(Payment.yookassa_payment_id == yookassa_payment_id).first()
        if not payment or payment.status == "completed":
            return False

        user = db.query(User).filter(User.id == payment.user_id).first()
        if not user:
            return False

        # Применяем benefits в зависимости от типа платежа
        if payment.payment_type == "reveal":
            user.available_reveals += 1
        elif payment.payment_type == "day_sub":
            if user.premium_until and user.premium_until > datetime.utcnow():
                user.premium_until += timedelta(days=1)
            else:
                user.premium_until = datetime.utcnow() + timedelta(days=1)
        elif payment.payment_type == "month_sub":
            if user.premium_until and user.premium_until > datetime.utcnow():
                user.premium_until += timedelta(days=30)
            else:
                user.premium_until = datetime.utcnow() + timedelta(days=30)

        payment.status = "completed"
        payment.completed_at = datetime.utcnow()

        db.commit()
        return True

    def is_user_premium(self, user: User):
        """Проверка премиум статуса"""
        if not user.premium_until:
            return False
        return user.premium_until > datetime.utcnow()

    def can_reveal_sender(self, user: User):
        """Может ли пользователь раскрыть отправителя"""
        return self.is_user_premium(user) or user.available_reveals > 0

    def use_reveal(self, db: Session, user: User):
        """Использование одного раскрытия"""
        if self.is_user_premium(user):
            return True  # Премиум пользователи могут раскрывать бесплатно

        if user.available_reveals > 0:
            user.available_reveals -= 1
            db.commit()
            return True
        return False


payment_service = PaymentService()