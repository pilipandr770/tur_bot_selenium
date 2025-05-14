# app/health.py
from flask import Blueprint, jsonify, current_app
from app.models import Article
import datetime
import os
import shutil

health_bp = Blueprint('health', __name__)

@health_bp.route('/')
def health_check():
    """
    Эндпоинт для проверки работоспособности приложения
    """
    try:
        # Проверяем доступ к базе данных
        article_count = Article.query.count()
        
        # Проверяем доступ к конфигурации
        app_config_ok = bool(current_app.config.get('OPENAI_API_KEY'))
        
        # Проверяем дисковое пространство для хранения изображений
        images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images')
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        disk_usage = shutil.disk_usage(images_dir)
        disk_free_gb = disk_usage.free / (1024 * 1024 * 1024)  # Convert to GB
        
        # Данные о статусе приложения
        status = {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': {
                'connected': True,
                'articles_count': article_count
            },
            'config': {
                'openai_api_configured': app_config_ok,
                'telegram_configured': bool(current_app.config.get('TELEGRAM_TOKEN'))
            },
            'disk': {
                'free_space_gb': round(disk_free_gb, 2),
                'status': 'ok' if disk_free_gb > 1.0 else 'warning'
            },
            'version': '1.0.0'
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500
