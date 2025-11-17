#!/usr/bin/env python3
import os
import time
import subprocess
import logging
import asyncio
import sys
from datetime import datetime

# Добавляем путь к проекту
sys.path.append('/home/yourusername/anon_bot')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/yourusername/anon_bot/logs/monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BotMonitor:
    def __init__(self):
        self.bot_script = '/home/yourusername/anon_bot/bot_runner.py'
        self.check_interval = 300  # 5 минут
        self.max_restarts_per_hour = 3
        self.restart_count = 0
        self.last_restart_time = time.time()
        self.last_daily_restart = None

        # Загружаем конфигурацию для уведомлений
        from app.config import BOT_TOKEN, ADMIN_IDS
        self.bot_token = BOT_TOKEN
        self.admin_ids = ADMIN_IDS

    async def send_admin_notification(self, message):
        """Отправляет уведомление всем админам"""
        if not self.bot_token or not self.admin_ids:
            logger.warning("❌ Cannot send notification: bot token or admin ids not configured")
            return

        try:
            from aiogram import Bot
            bot = Bot(token=self.bot_token)
            for admin_id in self.admin_ids:
                try:
                    await bot.send_message(
                        admin_id,
                        f"🔔 **Монитор бота**\n\n{message}",
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"❌ Error sending notification to admin {admin_id}: {e}")
            await bot.session.close()
        except Exception as e:
            logger.error(f"❌ Error in send_admin_notification: {e}")

    def is_bot_running(self):
        """Проверяет, запущен ли бот"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'bot_runner.py'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"❌ Error checking bot process: {e}")
            return False

    def start_bot(self):
        """Запускает бота"""
        try:
            cmd = [
                '/bin/bash', '-c',
                f'cd /home/yourusername/anon_bot && source venv/bin/activate && python {self.bot_script} >> logs/bot_console.log 2>&1 &'
            ]

            subprocess.Popen(cmd, shell=True)

            current_time = time.time()
            if current_time - self.last_restart_time < 3600:  # 1 час
                self.restart_count += 1
            else:
                self.restart_count = 1
                self.last_restart_time = current_time

            logger.info(f"✅ Bot started (restart #{self.restart_count} this hour)")
            return True

        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            return False

    def stop_bot(self):
        """Останавливает бота"""
        try:
            subprocess.run(['pkill', '-f', 'bot_runner.py'], capture_output=True)
            time.sleep(5)

            # Двойная проверка и принудительное завершение если нужно
            if self.is_bot_running():
                subprocess.run(['pkill', '-9', '-f', 'bot_runner.py'], capture_output=True)
                time.sleep(2)

            logger.info("✅ Bot stopped")
            return True
        except Exception as e:
            logger.error(f"❌ Error stopping bot: {e}")
            return False

    def check_restart_limit(self):
        """Проверяет лимит перезапусков"""
        if self.restart_count >= self.max_restarts_per_hour:
            logger.error("🚨 Too many restarts per hour. Waiting...")
            return False
        return True

    def should_do_daily_restart(self):
        """Проверяет, нужно ли делать ежедневный перезапуск в 00:00"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # Проверяем время между 00:00 и 00:05
        if current_time >= "00:00" and current_time <= "00:05":
            today = now.date()
            if self.last_daily_restart != today:
                self.last_daily_restart = today
                return True
        return False

    async def perform_daily_restart(self):
        """Выполняет ежедневный перезапуск"""
        logger.info("🔄 Performing daily scheduled restart...")

        message = (
            "🔄 **Ежедневный перезапуск бота**\n\n"
            "• Время: 00:00\n"
            "• Причина: Плановое обслуживание\n"
            "• Ожидаемое время простоя: 10-30 секунд"
        )

        await self.send_admin_notification(message)

        # Останавливаем бота
        self.stop_bot()
        time.sleep(10)

        # Запускаем заново
        if self.start_bot():
            success_message = "✅ **Бот успешно перезапущен**\n\nСистема работает в штатном режиме."
            await self.send_admin_notification(success_message)
        else:
            error_message = "❌ **Ошибка при перезапуске бота!**\n\nТребуется вмешательство администратора."
            await self.send_admin_notification(error_message)

    async def handle_bot_crash(self):
        """Обрабатывает аварийное падение бота"""
        logger.warning("❌ Bot is not running!")

        if self.check_restart_limit():
            # Отправляем уведомление о падении
            crash_message = (
                    "🚨 **Бот перестал работать!**\n\n"
                    "• Причина: Аварийное завершение\n"
                    "• Время: " + datetime.now().strftime("%d.%m.%Y %H:%M") + "\n"
                                                                              "• Действие: Автоматический перезапуск"
            )
            await self.send_admin_notification(crash_message)

            self.stop_bot()
            time.sleep(5)

            if self.start_bot():
                restart_message = (
                    "✅ **Бот перезапущен после падения**\n\n"
                    f"• Перезапуск №{self.restart_count} за последний час\n"
                    "• Система восстановлена"
                )
                await self.send_admin_notification(restart_message)
            else:
                error_message = (
                    "❌ **Не удалось перезапустить бота!**\n\n"
                    "• Критическая ошибка\n"
                    "• Требуется срочное вмешательство"
                )
                await self.send_admin_notification(error_message)
        else:
            limit_message = (
                "🚨 **Превышен лимит перезапусков!**\n\n"
                "• Причина: Слишком частые падения\n"
                "• Лимит: 3 перезапуска в час\n"
                "• Требуется ручное вмешательство"
            )
            await self.send_admin_notification(limit_message)
            time.sleep(3600)  # Ждем 1 час
            self.restart_count = 0

    def run(self):
        """Основной цикл мониторинга"""
        logger.info("👁️ Starting bot monitor...")

        # Первый запуск
        if not self.is_bot_running():
            asyncio.run(self.send_admin_notification(
                "🚀 **Монитор бота запущен**\n\nСистема мониторинга активирована."
            ))
            self.start_bot()

        while True:
            try:
                # Проверяем ежедневный перезапуск
                if self.should_do_daily_restart():
                    asyncio.run(self.perform_daily_restart())

                # Проверяем состояние бота
                if not self.is_bot_running():
                    asyncio.run(self.handle_bot_crash())

                # Ждем перед следующей проверкой
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                asyncio.run(self.send_admin_notification(
                    "🛑 **Монитор остановлен**\n\nРучная остановка мониторинга."
                ))
                logger.info("🛑 Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitor error: {e}")
                time.sleep(60)


if __name__ == "__main__":
    monitor = BotMonitor()
    monitor.run()
