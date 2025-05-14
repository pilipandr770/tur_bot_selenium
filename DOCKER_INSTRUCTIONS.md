# Инструкции по запуску в Docker

## Предварительные требования

- Установленный Docker
- Установленный Docker Compose

## Особенности безопасности

- Использование конкретной и стабильной версии Python (3.13-slim-bookworm)
- Запуск приложения от непривилегированного пользователя
- Ограничение ресурсов для стабильной работы
- Привязка веб-сервера только к локальному интерфейсу
- Ограничение привилегий контейнера
- Автоматический мониторинг работоспособности (healthcheck)

## Шаги по запуску

1. Настройте переменные окружения в файле `.env`:

```
OPENAI_API_KEY=ваш_ключ_openai
TELEGRAM_BOT_TOKEN=ваш_токен_бота
TELEGRAM_CHAT_ID=ваш_id_чата
```

2. Соберите образ Docker:

```bash
docker-compose build
```

3. Запустите контейнер:

```bash
docker-compose up -d
```

4. Проверьте логи:

```bash
docker-compose logs -f
```

## Остановка контейнера

```bash
docker-compose down
```

## Управление данными

Данные сохраняются в монтированных томах:
- `./logs` - логи приложения
- `./images` - сгенерированные изображения
- `./instance` - файл базы данных SQLite

## Мониторинг и проверка работоспособности

После запуска вы можете мониторить работу контейнера:

```bash
# Просмотр логов
docker-compose logs -f

# Просмотр статуса контейнера
docker ps

# Проверка состояния работоспособности
curl http://localhost:5000/

# Мониторинг потребления ресурсов
docker stats turizm_bot

# Использование скрипта управления
docker-compose exec app python manage.py health
```

### Интерпретация результатов мониторинга

Эндпоинт здоровья (`/`) возвращает JSON со следующей структурой:

```json
{
  "status": "healthy",
  "timestamp": "2023-09-15T12:34:56.789012",
  "database": {
    "connected": true,
    "articles_count": 42
  },
  "config": {
    "openai_api_configured": true,
    "telegram_configured": true
  },
  "disk": {
    "free_space_gb": 10.45,
    "status": "ok"
  },
  "version": "1.0.0"
}
```

### Утилиты администрирования

Для управления приложением используйте скрипт `manage.py`:

```bash
# Проверка состояния системы
docker-compose exec app python manage.py health

# Очистка старых изображений (старше 30 дней)
docker-compose exec app python manage.py clean --images=30

# Обрезка лог-файлов (сохранить последние 1000 строк)
docker-compose exec app python manage.py clean --logs
```

- `status`: "healthy" или "unhealthy"
- `timestamp`: время проверки в ISO формате
- `database.connected`: статус соединения с базой данных
- `database.articles_count`: количество статей в базе
- `config.*`: статус настроек различных API

## Решение проблем

1. Если контейнер не запускается, проверьте логи:
```bash
docker-compose logs
```

2. Для перезапуска сервиса:
```bash
docker-compose restart app
```

3. Для доступа к консоли внутри контейнера:
```bash
docker-compose exec app bash
```
