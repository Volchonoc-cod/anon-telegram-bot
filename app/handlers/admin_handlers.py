from aiogram import F, Router, types
from aiogram.filters import Command
from sqlalchemy.orm import Session
from sqlalchemy import func
from aiogram.types import InputFile  # ← ДОБАВЬТЕ ЭТО
import os  # ← ДОБАВЬТЕ ЭТО
from app.database import get_db
from app.models import User, AnonMessage
from app.config import ADMIN_IDS
from app.models import Payment
from app.backup_service import backup_service
from app.database_cleaner import db_cleaner
from datetime import datetime

router = Router()


def is_admin(user_id: int):
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return

    db = next(get_db())

    # Статистика
    total_users = db.query(User).count()
    total_messages = db.query(AnonMessage).count()
    users_with_links = db.query(User).filter(User.anon_link_uid.isnot(None)).count()
    reported_messages = db.query(AnonMessage).filter(AnonMessage.is_reported == True).count()

    # НОВАЯ СТАТИСТИКА ПО ПЛАТЕЖАМ
    premium_users = db.query(User).filter(User.premium_until > datetime.utcnow()).count()
    total_payments = db.query(Payment).filter(Payment.status == "completed").count()
    total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == "completed").scalar() or 0

    # Размер базы данных
    db_size = backup_service.get_db_size()

    text = (
        "👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"📨 Сообщений: <b>{total_messages}</b>\n"
        f"🔗 Пользователей с ссылками: <b>{users_with_links}</b>\n"
        f"🚫 Жалоб на сообщения: <b>{reported_messages}</b>\n"
        f"⭐ Премиум пользователей: <b>{premium_users}</b>\n"
        f"💰 Всего платежей: <b>{total_payments}</b>\n"
        f"📈 Общая выручка: <b>{total_revenue / 100:.2f}₽</b>\n"
        f"💾 Размер базы: <b>{db_size:.2f} MB</b>\n\n"
        "Команды:\n"
        "/admin_users - список пользователей\n"
        "/admin_messages - все сообщения\n"
        "/admin_reports - жалобы\n"
        "/admin_payments - платежи\n"
        "/backup - резервная копия\n"
        "/db_status - статус базы\n"
        "/cleanup_old_data - очистка старых данных"
    )

    await message.answer(text, parse_mode="HTML")


@router.message(Command("backup"))
async def manual_backup(message: types.Message):
    """Ручное создание резервной копии (только отчет)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return

    await message.answer("🔄 Создаю резервную копию базы данных...")

    # Создаем backup
    backup_path = backup_service.create_backup()
    size_mb = backup_service.get_db_size()
    stats = backup_service.get_db_stats()

    if backup_path:
        file_size = os.path.getsize(backup_path) / (1024 * 1024)  # Размер в MB

        # Формируем подробный отчет БЕЗ Markdown разметки
        report = (
            "✅ <b>Резервная копия создана!</b>\n\n"
            f"📊 <b>Размер базы:</b> {size_mb:.2f} MB\n"
            f"📦 <b>Размер копии:</b> {file_size:.2f} MB\n"
            f"📅 <b>Дата создания:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"💾 <b>Имя файла:</b> {os.path.basename(backup_path)}\n\n"
            f"📈 <b>Статистика базы:</b>\n"
            f"• 👥 Пользователей: {stats.get('users', 'N/A')}\n"
            f"• 📨 Сообщений: {stats.get('messages', 'N/A')}\n"
            f"• 💰 Успешных платежей: {stats.get('payments', 'N/A')}\n"
            f"• ⏳ Ожидающих платежей: {stats.get('pending_payments', 'N/A')}\n\n"
            f"💡 Резервная копия сохранена на сервере в папке <code>backups/</code>"
        )

        await message.answer(report, parse_mode="HTML")
    else:
        await message.answer("❌ Ошибка создания резервной копии")


@router.message(Command("db_status"))
async def db_status(message: types.Message):
    """Показать статус базы данных"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return

    size_mb = backup_service.get_db_size()
    stats = backup_service.get_db_stats()

    # Получаем список резервных копий
    backup_files = []
    backup_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backups')
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.startswith('bot_backup_') and filename.endswith('.db'):
                filepath = os.path.join(backup_dir, filename)
                file_size = os.path.getsize(filepath) / (1024 * 1024)
                backup_files.append((filename, file_size))

    status_text = (
        "📊 <b>Статус базы данных</b>\n\n"
        f"• Размер: {size_mb:.2f} MB\n"
        f"• Лимит предупреждения: {backup_service.max_size_mb} MB\n"
        f"• Критический лимит: {backup_service.critical_size_mb} MB\n\n"
        f"📈 <b>Статистика:</b>\n"
        f"• 👥 Пользователей: {stats.get('users', 'N/A')}\n"
        f"• 📨 Сообщений: {stats.get('messages', 'N/A')}\n"
        f"• 💰 Платежей: {stats.get('payments', 'N/A')}\n\n"
        f"💾 <b>Резервные копии:</b> {len(backup_files)} файлов\n"
    )

    # Добавляем информацию о последних копиях
    if backup_files:
        backup_files.sort(reverse=True)  # Сортируем по дате (новые сначала)
        status_text += f"📅 Последняя: {backup_files[0][0]} ({backup_files[0][1]:.1f} MB)"

    if size_mb > backup_service.critical_size_mb:
        status_text += "\n\n🚨 <b>КРИТИЧЕСКИЙ РАЗМЕР!</b>"
    elif size_mb > backup_service.max_size_mb:
        status_text += "\n\n⚠️ <b>Большой размер</b>"
    else:
        status_text += "\n\n✅ <b>Размер в норме</b>"

    await message.answer(status_text, parse_mode="HTML")


@router.message(Command("cleanup_old_data"))
async def cleanup_old_data(message: types.Message):
    """Очистка старых данных"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return

    await message.answer("🔄 Очищаю старые данные...")

    deleted_messages, deleted_payments = await db_cleaner.cleanup_old_data()

    await message.answer(
        f"🧹 **Очистка завершена**\n\n"
        f"• Удалено сообщений: {deleted_messages}\n"
        f"• Удалено платежей: {deleted_payments}\n"
        f"• Новый размер: {backup_service.get_db_size():.2f} MB"
    )


@router.message(Command("admin_payments"))
async def admin_payments(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    db = next(get_db())
    payments = db.query(Payment).filter(Payment.status == "completed").order_by(Payment.completed_at.desc()).limit(
        10).all()

    text = "💰 <b>Последние 10 платежей:</b>\n\n"

    for payment in payments:
        user = db.query(User).filter(User.id == payment.user_id).first()
        amount_rub = payment.amount / 100

        type_names = {
            "reveal": "Раскрытие",
            "day_sub": "Подписка 1 день",
            "month_sub": "Подписка месяц"
        }

        text += f"💳 {type_names.get(payment.payment_type, payment.payment_type)}\n"
        text += f"   👤 {user.first_name} (@{user.username})\n"
        text += f"   💰 {amount_rub:.2f}₽\n"
        text += f"   🕐 {payment.completed_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("admin_users"))
async def admin_users(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    db = next(get_db())
    users = db.query(User).order_by(User.created_at.desc()).limit(10).all()

    text = "👥 <b>Последние 10 пользователей:</b>\n\n"

    for user in users:
        messages_count = db.query(AnonMessage).filter(AnonMessage.receiver_id == user.id).count()
        has_link = "✅" if user.anon_link_uid else "❌"
        text += f"👤 {user.first_name} (@{user.username})\n"
        text += f"   ID: {user.telegram_id}\n"
        text += f"   Сообщений: {messages_count}\n"
        text += f"   Ссылка: {has_link}\n"
        text += f"   Регистрация: {user.created_at.strftime('%d.%m.%Y')}\n\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("admin_messages"))
async def admin_messages(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    db = next(get_db())
    messages = db.query(AnonMessage).order_by(AnonMessage.timestamp.desc()).limit(5).all()

    text = "📨 <b>Последние 5 сообщений:</b>\n\n"

    for msg in messages:
        receiver = db.query(User).filter(User.id == msg.receiver_id).first()

        if msg.sender_id:
            sender = db.query(User).filter(User.id == msg.sender_id).first()
            sender_info = f"👤 {sender.first_name}" if sender else "Неизвестно"
        else:
            sender_info = "🕵️ Аноним"

        anonymity = "🕵️ Анонимное" if msg.is_anonymous and not msg.is_revealed else "👤 Открытое"
        reported = " 🚫" if msg.is_reported else ""

        text += f"{anonymity}{reported} сообщение:\n"
        text += f"   📝 {msg.text[:50]}...\n"
        text += f"   👤 Отправитель: {sender_info}\n"
        text += f"   👥 Получатель: {receiver.first_name if receiver else 'Неизвестно'}\n"
        text += f"   🕐 {msg.timestamp.strftime('%d.%m.%Y %H:%M')}\n\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("admin_reports"))
async def admin_reports(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    db = next(get_db())
    reported_messages = db.query(AnonMessage).filter(AnonMessage.is_reported == True).order_by(
        AnonMessage.timestamp.desc()).all()

    if not reported_messages:
        await message.answer("🚫 Нет жалоб на сообщения")
        return

    text = "🚫 <b>Жалобы на сообщения:</b>\n\n"

    for i, msg in enumerate(reported_messages, 1):
        receiver = db.query(User).filter(User.id == msg.receiver_id).first()

        if msg.sender_id:
            sender = db.query(User).filter(User.id == msg.sender_id).first()
            sender_info = f"👤 {sender.first_name}" if sender else "Неизвестно"
        else:
            sender_info = "🕵️ Аноним"

        text += f"{i}. ID: {msg.id}\n"
        text += f"   📝 {msg.text[:100]}...\n"
        text += f"   👤 Отправитель: {sender_info}\n"
        text += f"   👥 Получатель: {receiver.first_name if receiver else 'Неизвестно'}\n"
        text += f"   🕐 {msg.timestamp.strftime('%d.%m.%Y %H:%M')}\n\n"

    await message.answer(text, parse_mode="HTML")
