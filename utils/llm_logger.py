"""
Модуль для логирования запросов и ответов LLM.
Логи сохраняются в файлы с ротацией (храним только 2 дня).
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


class MillisecondsFormatter(logging.Formatter):
    """Форматтер с миллисекундами в формате: 2025-12-06 06:24:20,670"""
    
    def formatTime(self, record, datefmt=None):
        """Переопределяем форматирование времени для добавления миллисекунд."""
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime('%Y-%m-%d %H:%M:%S')
            s = f"{t},{ct.microsecond // 1000:03d}"
        return s


@dataclass
class LLMLogParams:
    """Параметры для логирования запроса к LLM."""
    order_id: int
    model_name: str
    prompt: str
    response: str
    error: str | None = None
    duration_ms: float | None = None
    conversation_history: list | None = None

# Директория для логов (будет монтироваться как volume)
LOG_DIR = os.getenv('LLM_LOG_DIR', './logs')
LOG_DIR_PATH = Path(LOG_DIR)

# Максимальная длина ответа для логирования (остальное обрезается)
MAX_RESPONSE_LENGTH = 500

# Настройка логгера для LLM
_llm_logger = None


def _get_llm_logger() -> logging.Logger:
    """Возвращает настроенный логгер для LLM."""
    global _llm_logger
    
    if _llm_logger is not None:
        return _llm_logger
    
    ensure_log_dir()
    
    # Создаем логгер
    logger = logging.getLogger('llm')
    logger.setLevel(logging.DEBUG)
    
    # Убираем обработчики, если они уже есть (чтобы не дублировать)
    logger.handlers.clear()
    
    # Создаем файловый обработчик
    log_path = get_log_path()
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Настраиваем формат: 2025-12-06 06:24:20,670 - DEBUG - LLM API response: ...
    formatter = MillisecondsFormatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.propagate = False  # Не передаем логи в корневой логгер
    
    # Принудительно синхронизируем логи с диском для корректной работы с volume
    file_handler.flush()
    
    _llm_logger = logger
    return logger


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
                except Exception as e:
                    logging.warning(f"Ошибка при удалении {log_file.name}: {e}")
    except Exception as e:
        logging.warning(f"Ошибка при очистке старых логов: {e}")


def _truncate_text(text: str, max_length: int = MAX_RESPONSE_LENGTH) -> str:
    """
    Обрезает текст до указанной длины и добавляет '...' если текст был обрезан.
    
    Args:
        text: Текст для обрезки
        max_length: Максимальная длина текста
    
    Returns:
        Обрезанный текст с '...' в конце, если был обрезан
    """
    if not text:
        return text
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."


def log_llm_request(params: LLMLogParams) -> None:
    """
    Логирует запрос к LLM и ответ.
    
    Args:
        params: Параметры логирования запроса к LLM
    """
    try:
        ensure_log_dir()
        clean_old_logs()  # Периодически очищаем старые логи
        
        logger = _get_llm_logger()
        
        # Обрезаем длинные ответы
        truncated_response = _truncate_text(params.response, MAX_RESPONSE_LENGTH)
        truncated_prompt = _truncate_text(params.prompt, MAX_RESPONSE_LENGTH)
        
        # Определяем уровень логирования
        if params.error:
            log_level = logging.ERROR
            message = (
                f"LLM API error - Order ID: {params.order_id}, "
                f"Model: {params.model_name}, "
                f"Error: {params.error}"
            )
        else:
            log_level = logging.DEBUG
            duration_str = f"{params.duration_ms:.2f}ms" if params.duration_ms else "N/A"
            message = (
                f"LLM API response - Order ID: {params.order_id}, "
                f"Model: {params.model_name}, "
                f"Duration: {duration_str}"
            )
        
        # Логируем основную информацию
        logger.log(log_level, message)
        
        # Логируем промпт (INFO уровень)
        logger.info(f"LLM API prompt - Order ID: {params.order_id}, Prompt: {truncated_prompt}")
        
        # Логируем ответ (DEBUG уровень, если нет ошибки)
        if not params.error:
            logger.debug(f"LLM API response - Order ID: {params.order_id}, Response: {truncated_response}")
        
        # Логируем дополнительную информацию (DEBUG уровень)
        if params.conversation_history:
            conv_length = len(params.conversation_history)
            logger.debug(f"LLM API context - Order ID: {params.order_id}, Conversation length: {conv_length}")
        
        # Принудительно синхронизируем логи с диском для корректной работы с volume
        for handler in logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
            
    except Exception as e:
        # Не падаем, если логирование не удалось
        logging.error(f"Ошибка при логировании LLM запроса: {e}")

