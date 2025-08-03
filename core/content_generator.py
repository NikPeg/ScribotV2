"""
Модуль для генерации содержания работ через GPT.
"""

from gpt.assistant import ask_assistant


async def generate_work_plan(thread_id: str, model_name: str, theme: str, pages: int, work_type: str) -> str:
    """
    Генерирует план работы через GPT.
    
    Args:
        thread_id: ID потока OpenAI
        model_name: Название модели GPT
        theme: Тема работы
        pages: Количество страниц
        work_type: Тип работы (курсовая, дипломная и т.д.)
    
    Returns:
        Сгенерированный план работы
    """
    plan_prompt = (
        f"Составь подробный план для {work_type.lower()} на тему '{theme}' "
        f"объемом {pages} страниц. План должен состоять из введения, "
        f"3-4 глав (каждая с 2-3 подразделами) и заключения."
    )
    
    return await ask_assistant(thread_id, plan_prompt, model_name)


async def generate_full_work_content(thread_id: str, model_name: str, theme: str, pages: int, work_type: str) -> str:
    """
    Генерирует полное содержание работы через GPT.
    
    Args:
        thread_id: ID потока OpenAI
        model_name: Название модели GPT
        theme: Тема работы
        pages: Количество страниц
        work_type: Тип работы (курсовая, дипломная и т.д.)
    
    Returns:
        Полное содержание работы в формате LaTeX
    """
    # Промпт для генерации полной работы
    full_work_prompt = f"""
Напиши полную {work_type.lower()} на тему "{theme}" объемом примерно {pages} страниц.

Структура должна включать:
1. Введение (1-2 страницы)
2. Основная часть (3-4 главы, каждая 2-3 страницы)
3. Заключение (1-2 страницы)
4. Список литературы

ВАЖНЫЕ требования к форматированию:
- Текст должен быть в формате LaTeX (без преамбулы и \\begin{{document}})
- Используй команды \\section{{}} для глав, \\subsection{{}} для подразделов
- НЕ используй длинные строки текста - разбивай абзацы на короткие строки (максимум 80 символов)
- После каждого предложения делай перенос строки
- Включи формулы, таблицы или рисунки где уместно
- Текст должен быть академическим и структурированным
- Добавь реальные источники в список литературы

Начни прямо с введения:
"""
    
    return await ask_assistant(thread_id, full_work_prompt, model_name)