#!/bin/bash

# daily_restart.sh - Скрипт для ежедневного перезапуска через cron

cd /home/yourusername/anon_bot

LOG_FILE="/home/yourusername/anon_bot/logs/daily_restart.log"

echo "==========================================" >> $LOG_FILE
echo "Daily restart started at $(date)" >> $LOG_FILE

# Останавливаем монитор (он сам перезапустит бота)
pkill -f "bot_monitor.py"

sleep 5

# Запускаем монитор заново
source venv/bin/activate
nohup python bot_monitor.py >> logs/monitor_console.log 2>&1 &

echo "Daily restart completed at $(date)" >> $LOG_FILE
echo "==========================================" >> $LOG_FILE