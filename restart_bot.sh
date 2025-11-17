#!/bin/bash

# restart_bot.sh - Скрипт перезапуска бота с уведомлениями

cd /home/yourusername/anon_bot

# Логируем перезапуск
echo "$(date): Restarting bot..." >> logs/restart.log

# Создаем директорию для логов если нет
mkdir -p logs

# Останавливаем бота и монитор
echo "Stopping bot and monitor..."
pkill -f "bot_runner.py"
pkill -f "bot_monitor.py"

# Ждем завершения
sleep 5

# Принудительно завершаем если все еще работают
pkill -9 -f "bot_runner.py" 2>/dev/null
pkill -9 -f "bot_monitor.py" 2>/dev/null

sleep 3

# Запускаем монитор
echo "Starting monitor..."
source venv/bin/activate
nohup python bot_monitor.py >> logs/monitor_console.log 2>&1 &

echo "✅ Bot and monitor restarted at $(date)"

# Ждем немного и проверяем статус
sleep 10
if pgrep -f "bot_monitor.py" > /dev/null; then
    echo "✅ Monitor is running"
else
    echo "❌ Monitor failed to start"
fi
