#!/usr/bin/env python
"""
Скрипт для управления приложением туристического сайта
- Проверка состояния приложения
- Очистка старых данных
- Принудительный запуск задач
"""

import argparse
import os
import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta

def check_health():
    """Проверка состояния приложения"""
    try:
        response = requests.get('http://localhost:5000/')
        response.raise_for_status()
        health_data = response.json()
        
        # Вывод информации о состоянии
        print(f"\n===== Состояние приложения ({health_data['timestamp']}) =====")
        print(f"Статус: {health_data['status'].upper()}")
        print(f"Версия: {health_data.get('version', 'неизвестно')}")
        
        # Информация о базе данных
        print("\n----- База данных -----")
        print(f"Подключена: {health_data['database']['connected']}")
        print(f"Количество статей: {health_data['database']['articles_count']}")
        
        # Информация о дисковом пространстве
        print("\n----- Дисковое пространство -----")
        print(f"Свободно: {health_data['disk']['free_space_gb']} ГБ")
        print(f"Статус: {health_data['disk']['status'].upper()}")
        
        # Информация о конфигурации
        print("\n----- Конфигурация API -----")
        print(f"OpenAI API настроен: {health_data['config']['openai_api_configured']}")
        print(f"Telegram API настроен: {health_data['config']['telegram_configured']}")
        
        return True
    except Exception as e:
        print(f"Ошибка при проверке состояния: {e}")
        return False

def clean_old_images(days=30):
    """Очистка старых изображений"""
    images_dir = Path('images')
    if not images_dir.exists():
        print("Директория с изображениями не найдена")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    removed = 0
    
    print(f"\nПоиск изображений старше {days} дней...")
    for image_file in images_dir.glob('*.png'):
        if image_file.stat().st_mtime < cutoff_date.timestamp():
            image_file.unlink()
            removed += 1
    
    print(f"Удалено старых изображений: {removed}")

def truncate_logs():
    """Очистка старых логов"""
    logs_dir = Path('logs')
    if not logs_dir.exists():
        print("Директория с логами не найдена")
        return
    
    for log_file in logs_dir.glob('*.log'):
        # Сохраняем последние 1000 строк
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-1000:]
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print(f"Лог {log_file.name} обрезан до 1000 строк")
        except Exception as e:
            print(f"Ошибка при обработке {log_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Утилита управления туристическим сайтом')
    subparsers = parser.add_subparsers(dest='command', help='Команда для выполнения')
    
    # Команда health
    health_parser = subparsers.add_parser('health', help='Проверить состояние приложения')
    
    # Команда clean
    clean_parser = subparsers.add_parser('clean', help='Очистить старые данные')
    clean_parser.add_argument('--images', type=int, default=30, 
                             help='Удалить изображения старше указанного количества дней (по умолчанию 30)')
    clean_parser.add_argument('--logs', action='store_true', 
                             help='Очистить старые логи, оставив последние 1000 строк')
    
    args = parser.parse_args()
    
    if args.command == 'health':
        check_health()
    elif args.command == 'clean':
        if args.images:
            clean_old_images(args.images)
        if args.logs:
            truncate_logs()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
