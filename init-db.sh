#!/bin/bash
# init-db.sh - Скрипт для инициализации базы данных при первом запуске

# Переходим в директорию приложения
cd /app

# Создаем директории, если их нет
mkdir -p instance images debug logs

# Запускаем миграции базы данных
export FLASK_APP=app.run
flask db upgrade

echo "База данных инициализирована успешно!"
