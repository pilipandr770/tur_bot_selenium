# Используем официальный образ Python с конкретной версией
FROM python:3.10.13-slim-bookworm

# Устанавливаем непривилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Устанавливаем зависимости для Chrome/Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libgconf-2-4 \
    libxi6 \
    libglib2.0-0 \
    libnss3 \
    libxcb1 \
    libasound2 \
    libxtst6 \
    libgtk-3-0 \
    libxss1 \
    libgbm1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы с зависимостями
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Создаем директории для данных
RUN mkdir -p images debug logs

# Делаем скрипт управления исполняемым
RUN chmod +x manage.py

# Определяем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.run
ENV FLASK_ENV=production
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Разрешаем записывать в определенные директории
RUN mkdir -p images debug logs instance && \
    chown -R appuser:appuser /app

# Экспонируем порт
EXPOSE 5000

# Используем непривилегированного пользователя
USER appuser

# Запускаем приложение
CMD ["python", "-m", "app.run"]
