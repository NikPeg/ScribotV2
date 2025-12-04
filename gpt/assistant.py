import asyncio
import time
from openai import AsyncOpenAI
from typing import List, Dict
from core import settings
from utils.llm_logger import log_llm_request

# Инициализируем клиента OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.llm_token
)

# Общий system prompt для всех запросов
SYSTEM_PROMPT = (
    "Ты — эксперт по написанию студенческих работ. Твоя задача — генерировать "
    "содержимое для курсовых, дипломных и других работ в формате LaTeX. "
    "Следуй инструкциям пользователя, создавай структурированный и "
    "академически корректный текст. Генерируй только запрошенную часть, "
    "не добавляй лишних комментариев."
)

# Хранилище истории сообщений для каждого заказа
# Ключ: order_id, значение: список сообщений
conversation_history: Dict[int, List[Dict[str, str]]] = {}


def init_conversation(order_id: int, theme: str) -> None:
    """
    Инициализирует новую беседу для заказа.
    
    Args:
        order_id: ID заказа
        theme: Тема работы
    """
    conversation_history[order_id] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"Тема моей работы: «{theme}». Запомни её."
        }
    ]


def clear_conversation(order_id: int) -> None:
    """
    Очищает историю беседы для заказа.
    
    Args:
        order_id: ID заказа
    """
    if order_id in conversation_history:
        del conversation_history[order_id]


async def ask_assistant(order_id: int, prompt: str, model_name: str) -> str:
    """
    Отправляет промпт в модель через OpenRouter API и возвращает ответ.
    
    Args:
        order_id: ID заказа (для сохранения истории)
        prompt: Текст запроса
        model_name: Название модели (обязательный параметр)
    
    Returns:
        Ответ модели
    """
    
    # Убеждаемся, что история существует
    if order_id not in conversation_history:
        # Если истории нет, создаем базовую
        conversation_history[order_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]
    
    # Добавляем новый запрос пользователя в историю
    conversation_history[order_id].append({
        "role": "user",
        "content": prompt
    })
    
    start_time = time.time()
    error = None
    assistant_message = None
    
    try:
        # Отправляем запрос в OpenRouter
        response = await client.chat.completions.create(
            model=model_name,
            messages=conversation_history[order_id],
            temperature=0.7,
        )
        
        # Извлекаем ответ
        if response.choices and len(response.choices) > 0:
            assistant_message = response.choices[0].message.content
            
            # Добавляем ответ ассистента в историю
            conversation_history[order_id].append({
                "role": "assistant",
                "content": assistant_message
            })
            
        else:
            error = "Пустой ответ от модели"
            assistant_message = "Произошла ошибка при генерации ответа: пустой ответ от модели."
            
    except Exception as e:
        error = str(e)
        assistant_message = f"Произошла ошибка при генерации ответа: {str(e)}"
        print(f"Ошибка при запросе к OpenRouter API: {e}")
    
    finally:
        # Логируем запрос и ответ
        duration_ms = (time.time() - start_time) * 1000
        log_llm_request(
            order_id=order_id,
            model_name=model_name,
            prompt=prompt,
            response=assistant_message,
            error=error,
            duration_ms=duration_ms,
            conversation_history=conversation_history.get(order_id)
        )
    
    return assistant_message
