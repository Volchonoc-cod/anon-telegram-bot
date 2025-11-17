#!/usr/bin/env python3
import asyncio
import sys
import os
import logging
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(__file__))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/yourusername/anon_bot/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def send_startup_notification():
    """Отправляет уведомление о запуске бота"""
    try:
        from app.config import BOT_TOKEN, ADMIN_IDS
        from aiogram import Bot

        bot = Bot(token=BOT_TOKEN)
        message = (
            "🚀 **Бот запущен**\n\n"
            f"• Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            "• Статус: ✅ Работает\n"
            "• Мониторинг: Активен"
        )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, message, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"❌ Error sending startup notification to {admin_id}: {e}")

        await bot.session.close()
    except Exception as e:
        logger.error(f"❌ Error in startup notification: {e}")


async def run_bot():
    """Основная функция запуска бота"""
    try:
        from app.config import BOT_TOKEN
        from app.database import create_tables
        from app.handlers.main_handlers import router as main_router
        from app.handlers.anon_handlers import router as anon_router
        from app.handlers.payment_handlers import router as payment_router
        from app.handlers.admin_handlers import router as admin_router
        from app.backup_service import backup_service
        from app.database_cleaner import db_cleaner

        from aiogram import Bot, Dispatcher
        from aiogram.fsm.storage.memory import MemoryStorage
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        # Создаем необходимые директории
        os.makedirs('/home/yourusername/anon_bot/data', exist_ok=True)
        os.makedirs('/home/yourusername/anon_bot/backups', exist_ok=True)
        os.makedirs('/home/yourusername/anon_bot/logs', exist_ok=True)

        # Создаем таблицы в БД
        create_tables()
        logger.info("✅ Database tables created")

        # Инициализация бота и диспетчера
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        # Регистрация роутеров
        dp.include_router(anon_router)
        dp.include_router(main_router)
        dp.include_router(payment_router)
        dp.include_router(admin_router)

        # Создаем планировщик
        scheduler = AsyncIOScheduler()

        # Резервное копирование каждые 24 часа
        scheduler.add_job(
            backup_service.check_and_backup,
            'interval',
            hours=24,
            id='daily_backup',
            name='Ежедневное резервное копирование'
        )

        # Очистка старых данных каждые 7 дней
        scheduler.add_job(
            db_cleaner.cleanup_old_data,
            'interval',
            days=7,
            id='cleanup',
            name='Очистка старых данных'
        )

        # Запускаем планировщик
        scheduler.start()
        logger.info("✅ Scheduler started")

        # Получаем информацию о боте
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username} ({bot_info.first_name})")

        # Отправляем уведомление о запуске
        await send_startup_notification()

        # Сразу делаем первый backup
        logger.info("🔄 Running initial backup...")
        await backup_service.check_and_backup()

        # Запуск бота
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🚀 Bot started polling...")

        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Critical error in run_bot: {e}")

        # Отправляем уведомление об ошибке
        try:
            from app.config import BOT_TOKEN, ADMIN_IDS
            from aiogram import Bot

            bot = Bot(token=BOT_TOKEN)
            error_message = (
                "🚨 **Критическая ошибка бота**\n\n"
                f"• Ошибка: {str(e)}\n"
                "• Бот остановлен\n"
                "• Требуется перезапуск"
            )

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, error_message, parse_mode="Markdown")
                except:
                    pass

            await bot.session.close()
        except:
            pass

        raise


def main():
    """Точка входа для запуска из консоли"""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
    