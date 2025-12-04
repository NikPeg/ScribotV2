"""
Модуль для логирования запросов и ответов LLM.
Логи сохраняются в файлы с ротацией (храним только 2 дня).
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

# Директория для логов (будет монтироваться как volume)
LOG_DIR = os.getenv('LLM_LOG_DIR', './logs')
LOG_DIR_PATH = Path(LOG_DIR)


def ensure_log_dir():
    """Создает директорию для логов, если её нет."""
    LOG_DIR_PATH.mkdir(parents=True, exist_ok=True)


def get_log_filename() -> str:
    """
    Возвращает имя файла лога для текущего дня.
    Формат: llm_YYYY-MM-DD.log
    """
    today = datetime.now().strftime('%Y-%m-%d')
    return f"llm_{today}.log"


def get_log_path() -> Path:
    """Возвращает полный путь к файлу лога для текущего дня."""
    ensure_log_dir()
    return LOG_DIR_PATH / get_log_filename()


def clean_old_logs():
    """
    Удаляет логи старше 2 дней (оставляет только текущий и предыдущий день).
    """
    try:
        ensure_log_dir()
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Формируем имена файлов для сохранения
        keep_files = {
            f"llm_{today.strftime('%Y-%m-%d')}.log",
            f"llm_{yesterday.strftime('%Y-%m-%d')}.log"
        }
        
        # Удаляем все файлы логов, кроме нужных
        for log_file in LOG_DIR_PATH.glob("llm_*.log"):
            if log_file.name not in keep_files:
                try:
                    log_file.unlink()
                    print(f"Удален старый лог: {log_file.name}")
                except Exception as e:
                    print(f"Ошибка при удалении {log_file.name}: {e}")
    except Exception as e:
        print(f"Ошибка при очистке старых логов: {e}")


def log_llm_request(order_id: int, model_name: str, prompt: str, response: str, 
                   error: str = None, duration_ms: float = None, conversation_history: list = None):
    """
    Логирует запрос к LLM и ответ.
    
    Args:
        order_id: ID заказа
        model_name: Название модели
        prompt: Текст запроса
        response: Ответ модели (или None при ошибке)
        error: Текст ошибки (если была)
        duration_ms: Длительность запроса в миллисекундах
        conversation_history: Полная история беседы (опционально, для контекста)
    """
    try:
        ensure_log_dir()
        clean_old_logs()  # Периодически очищаем старые логи
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "order_id": order_id,
            "model": model_name,
            "prompt": prompt,
            "response": response,
            "error": error,
            "duration_ms": round(duration_ms, 2) if duration_ms else None,
            "success": error is None,
            "conversation_length": len(conversation_history) if conversation_history else 0
        }
        
        # Добавляем полную историю беседы для контекста (только последние 5 сообщений для экономии места)
        if conversation_history:
            log_entry["conversation_context"] = conversation_history[-5:]
        
        log_path = get_log_path()
        
        # Записываем в JSON Lines формат (каждая строка - отдельный JSON)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
    except Exception as e:
        # Не падаем, если логирование не удалось
        print(f"Ошибка при логировании LLM запроса: {e}")

