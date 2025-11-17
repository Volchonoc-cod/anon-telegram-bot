import asyncio
import logging
from aiogram import Bot
from app.config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_bot():
    """Тестирование работы бота"""
    bot = Bot(token=BOT_TOKEN)

    try:
        # Получаем информацию о боте
        me = await bot.get_me()
        logger.info(f"✅ Бот: @{me.username} ({me.first_name})")

        # Проверяем, что бот может отправлять сообщения
        await bot.send_message(5784508611, "🤖 Бот запущен и работает!")
        logger.info("✅ Тестовое сообщение отправлено")

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(test_bot())