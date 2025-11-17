import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения! Проверьте файл .env")

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# Настройки БД
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/bot.db")

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Вывод информации о конфигурации (для отладки)
print(f"✅ Конфигурация загружена: Bot Token = {BOT_TOKEN[:10]}...")
print(f"✅ Админы: {ADMIN_IDS}")
print(f"✅ База данных: {DATABASE_URL}")
print(f"✅ ЮKassa Shop ID: {YOOKASSA_SHOP_ID}")
