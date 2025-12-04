import asyncio
import time
from openai import AsyncOpenAI
from typing import List, Dict
from core import settings
from utils.llm_logger import log_llm_request
from core.test_data_generator import (
    TEST_MODEL_NAME,
    generate_test_plan,
    generate_test_bibliography,
    generate_test_content,
    generate_test_subsection,
    generate_test_subsections_list
)

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
    В тестовом режиме (model_name == "TEST") возвращает тестовые данные без запроса к API.
    
    Args:
        order_id: ID заказа (для сохранения истории)
        prompt: Текст запроса
        model_name: Название модели (обязательный параметр)
    
    Returns:
        Ответ модели или тестовые данные
    """
    
    # Проверяем тестовый режим
    if model_name == TEST_MODEL_NAME:
        return _generate_test_response(order_id, prompt)
    
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


def _generate_test_response(order_id: int, prompt: str) -> str:
    """
    Генерирует тестовый ответ на основе анализа промпта.
    В тестовом режиме не выполняет запросов к LLM.
    
    Args:
        order_id: ID заказа
        prompt: Текст запроса
    
    Returns:
        Тестовые данные в зависимости от типа запроса
    """
    prompt_lower = prompt.lower()
    
    # Пытаемся извлечь тему из истории разговора, если она там есть
    theme_from_history = None
    if order_id in conversation_history:
        for msg in conversation_history[order_id]:
            if msg.get('role') == 'user' and 'тема' in msg.get('content', '').lower():
                # Извлекаем тему из сообщения вида "Тема моей работы: «{theme}». Запомни её."
                import re
                match = re.search(r'«([^»]+)»', msg['content'])
                if match:
                    theme_from_history = match.group(1)
                    break
    
    # Извлекаем информацию из промпта
    theme = theme_from_history or _extract_theme_from_prompt(prompt)
    pages = _extract_pages_from_prompt(prompt)
    work_type = _extract_work_type_from_prompt(prompt)
    
    # Определяем тип запроса по ключевым словам
    if 'план' in prompt_lower or ('составь' in prompt_lower and 'план' in prompt_lower):
        # Генерация плана работы
        response = generate_test_plan(theme, pages or 20, work_type or "курсовая")
    elif 'список' in prompt_lower and ('источник' in prompt_lower or 'библиограф' in prompt_lower):
        # Генерация библиографии
        response = generate_test_bibliography(theme)
    elif 'подраздел' in prompt_lower and 'предложи' in prompt_lower:
        # Генерация списка подразделов
        chapter_title = _extract_chapter_title_from_prompt(prompt)
        response = generate_test_subsections_list(chapter_title or "Глава", theme)
    elif 'подраздел' in prompt_lower and 'напиши' in prompt_lower:
        # Генерация содержания подраздела
        subsection_title = _extract_subsection_title_from_prompt(prompt)
        chapter_title = _extract_chapter_title_from_prompt(prompt)
        target_pages = _extract_target_pages_from_prompt(prompt)
        response = generate_test_subsection(
            subsection_title or "Подраздел",
            chapter_title or "Глава",
            theme,
            target_pages or 1.0
        )
    else:
        # Генерация обычного содержания главы
        chapter_title = _extract_chapter_title_from_prompt(prompt)
        target_pages = _extract_target_pages_from_prompt(prompt)
        response = generate_test_content(
            chapter_title or "Глава",
            theme,
            target_pages or 2.0
        )
    
    # Логируем тестовый запрос (но не как реальный запрос к LLM)
    log_llm_request(
        order_id=order_id,
        model_name=TEST_MODEL_NAME,
        prompt=prompt,
        response=response,
        error=None,
        duration_ms=0,
        conversation_history=None
    )
    
    return response


def _extract_theme_from_prompt(prompt: str) -> str:
    """Извлекает тему работы из промпта."""
    # Ищем тему в кавычках
    import re
    match = re.search(r'тема[:\s]+["\']([^"\']+)["\']', prompt, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Ищем тему после слова "тема"
    match = re.search(r'тема[:\s]+([^\n]+)', prompt, re.IGNORECASE)
    if match:
        return match.group(1).strip().strip('"\'')
    
    return "Исследование"


def _extract_pages_from_prompt(prompt: str) -> int:
    """Извлекает количество страниц из промпта."""
    import re
    match = re.search(r'(\d+)\s*страниц', prompt, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    match = re.search(r'объемом\s+(\d+)', prompt, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    return None


def _extract_work_type_from_prompt(prompt: str) -> str:
    """Извлекает тип работы из промпта."""
    import re
    work_types = ['курсовая', 'дипломная', 'реферат', 'доклад', 'исследование']
    for wt in work_types:
        if wt in prompt.lower():
            return wt
    return None


def _extract_chapter_title_from_prompt(prompt: str) -> str:
    """Извлекает название главы из промпта."""
    import re
    # Ищем в кавычках
    match = re.search(r'["\']([^"\']+)["\']', prompt)
    if match:
        return match.group(1)
    
    # Ищем после слова "глава"
    match = re.search(r'глава[:\s]+["\']?([^"\'\n]+)["\']?', prompt, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return None


def _extract_subsection_title_from_prompt(prompt: str) -> str:
    """Извлекает название подраздела из промпта."""
    import re
    # Ищем в кавычках
    match = re.search(r'подраздел[:\s]+["\']([^"\']+)["\']', prompt, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def _extract_target_pages_from_prompt(prompt: str) -> float:
    """Извлекает целевое количество страниц из промпта."""
    import re
    # Ищем "примерно X страниц" или "X символов"
    match = re.search(r'примерно\s+(\d+(?:\.\d+)?)\s*(?:страниц|символов)', prompt, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    # Ищем "X символов" и конвертируем в страницы (1500 символов = 1 страница)
    match = re.search(r'(\d+)\s*символов', prompt, re.IGNORECASE)
    if match:
        return float(match.group(1)) / 1500.0
    
    return None
