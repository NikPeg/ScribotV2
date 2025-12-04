"""
Модуль для генерации содержания работ через GPT с контролем объема.
"""

from typing import List, Dict, Tuple
from gpt.assistant import ask_assistant
from core.page_calculator import (
    parse_work_plan, 
    calculate_pages_per_chapter, 
    count_pages_in_text,
    should_generate_subsections,
    is_chapter_complete
)


async def generate_work_plan(order_id: int, model_name: str, theme: str, pages: int, work_type: str) -> str:
    """
    Генерирует план работы через OpenRouter API.
    
    Args:
        order_id: ID заказа
        model_name: Название модели GPT
        theme: Тема работы
        pages: Количество страниц
        work_type: Тип работы (курсовая, дипломная и т.д.)
    
    Returns:
        Сгенерированный план работы
    """
    plan_prompt = (
        f"Составь подробный план для {work_type.lower()} на тему '{theme}' "
        f"объемом {pages} страниц. План должен состоять из:\n"
        f"1. Введение\n"
        f"2. 3-4 основные главы (каждая с 2-3 подразделами)\n"
        f"3. Заключение\n"
        f"4. Список использованных источников\n\n"
        f"Формат ответа:\n"
        f"1. Введение\n"
        f"2. Название первой главы\n"
        f"   2.1 Подраздел\n"
        f"   2.2 Подраздел\n"
        f"3. Название второй главы\n"
        f"   3.1 Подраздел\n"
        f"   3.2 Подраздел\n"
        f"И так далее..."
    )
    
    return await ask_assistant(order_id, plan_prompt, model_name)


async def generate_work_content_stepwise(
    order_id: int, 
    model_name: str, 
    theme: str, 
    pages: int, 
    work_type: str,
    plan_text: str,
    progress_callback=None
) -> str:
    """
    Генерирует содержание работы пошагово с контролем объема.
    
    Args:
        order_id: ID заказа
        model_name: Название модели GPT
        theme: Тема работы
        pages: Количество страниц
        work_type: Тип работы
        plan_text: Текст плана работы
        progress_callback: Функция для обновления прогресса
    
    Returns:
        Полное содержание работы в формате LaTeX
    """
    # Парсим план работы
    try:
        chapters = parse_work_plan(plan_text)
    except Exception:
        # Fallback к старому методу если план не распарсился
        return await generate_full_work_content_legacy(order_id, model_name, theme, pages, work_type)
    
    if not chapters:
        # Fallback к старому методу если план не распарсился
        return await generate_full_work_content_legacy(order_id, model_name, theme, pages, work_type)
    
    # Разделяем главы на основные и список источников
    main_chapters = []
    bibliography_chapter = None
    
    for chapter in chapters:
        if _is_bibliography_chapter(chapter['title']):
            bibliography_chapter = chapter
        else:
            main_chapters.append(chapter)
    
    # Рассчитываем страницы для основных глав (исключая список источников)
    pages_per_chapter = calculate_pages_per_chapter(pages - 0.5, main_chapters)  # Резервируем 0.5 стр для списка
    
    full_content = ""
    total_pages_generated = 0.0
    
    # Генерируем основные главы
    for i, chapter in enumerate(main_chapters):
        chapter_title = chapter['title']
        target_pages = pages_per_chapter.get(chapter_title, 2.0)
        
        if progress_callback:
            progress = int((i / len(main_chapters)) * 90)  # 90% для основных глав
            await progress_callback(f"Генерирую главу: {chapter_title[:50]}...", progress)
        
        # Генерируем основное содержание главы
        chapter_content = await generate_chapter_content(
            order_id, model_name, chapter_title, theme, target_pages, work_type
        )
        
        current_chapter_pages = count_pages_in_text(chapter_content)
        subsections_content = ""
        
        # Если страниц недостаточно, генерируем подразделы
        if should_generate_subsections(current_chapter_pages, target_pages):
            subsections_content = await generate_subsections_content(
                order_id, model_name, chapter_title, chapter['subsections'],
                target_pages - current_chapter_pages, theme
            )
            chapter_content += "\n\n" + subsections_content
            current_chapter_pages = count_pages_in_text(chapter_content)
        
        # Добавляем главу к общему содержанию
        full_content += chapter_content + "\n\n\\newpage\n\n"
        total_pages_generated += current_chapter_pages
        
        # Проверяем, не превысили ли общий объем
        if total_pages_generated >= pages * 1.1:
            break
    
    # Всегда добавляем список источников в конце
    if bibliography_chapter:
        if progress_callback:
            await progress_callback("Генерирую список источников...", 95)
        
        bibliography_content = await generate_chapter_content(
            order_id, model_name, bibliography_chapter['title'], theme, 0.5, work_type
        )
        full_content += bibliography_content
    else:
        # Если список источников не был в плане, создаем его
        if progress_callback:
            await progress_callback("Генерирую список источников...", 95)
        
        bibliography_content = await generate_chapter_content(
            order_id, model_name, "Список использованных источников", theme, 0.5, work_type
        )
        full_content += bibliography_content
    
    return full_content.strip()


async def generate_chapter_content(
    order_id: int, 
    model_name: str, 
    chapter_title: str, 
    theme: str, 
    target_pages: float,
    work_type: str
) -> str:
    """
    Генерирует содержание одной главы.
    
    Args:
        order_id: ID заказа
        model_name: Название модели GPT
        chapter_title: Название главы
        theme: Тема работы
        target_pages: Целевое количество страниц
        work_type: Тип работы
    
    Returns:
        Содержание главы в формате LaTeX
    """
    # Определяем тип главы для специальной обработки
    title_lower = chapter_title.lower()
    
    if 'введение' in title_lower:
        prompt = f"""
Напиши введение для {work_type.lower()} на тему "{theme}".

Введение должно содержать:
- Актуальность темы
- Цель и задачи работы
- Объект и предмет исследования
- Методы исследования
- Структуру работы

Объем: примерно {int(target_pages * 1500)} символов.
Формат: LaTeX (используй \\section{{Введение}} в начале).
НЕ используй длинные строки - разбивай на короткие (до 80 символов).
Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно.
"""
    
    elif 'заключение' in title_lower:
        prompt = f"""
Напиши заключение для {work_type.lower()} на тему "{theme}".

Заключение должно содержать:
- Краткие выводы по каждой главе
- Достижение поставленных целей и задач
- Практическую значимость результатов
- Перспективы дальнейших исследований

Объем: примерно {int(target_pages * 1500)} символов.
Формат: LaTeX (используй \\section{{Заключение}} в начале).
НЕ используй длинные строки - разбивай на короткие (до 80 символов).
Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно.
"""
    
    elif 'список' in title_lower or 'библиография' in title_lower:
        prompt = f"""
Создай список использованных источников для {work_type.lower()} на тему "{theme}".

Включи 15-20 источников:
- Научные статьи
- Монографии
- Учебники
- Интернет-ресурсы
- Нормативные документы (если применимо)

ВАЖНО: Используй формат LaTeX thebibliography для корректной работы ссылок!

Формат должен быть:
\\section{{Список использованных источников}}

\\begin{{thebibliography}}{{99}}
\\bibitem{{source1}} Ананьева, Т.И. Физиология высшей нервной деятельности / Т.И. Ананьева. - М.: Медицина, 2018. - 432 с.
\\bibitem{{source2}} Следующий источник...
\\end{{thebibliography}}

Каждый источник должен иметь уникальный ключ (source1, source2, source3 и т.д.) в команде \\bibitem{{ключ}}.
НЕ используй длинные строки - разбивай на короткие (до 80 символов).
"""
    
    else:
        prompt = f"""
Напиши главу "{chapter_title}" для {work_type.lower()} на тему "{theme}".

Глава должна быть содержательной и академической, включать:
- Теоретические основы
- Анализ существующих подходов
- Практические аспекты
- Примеры и иллюстрации

Объем: примерно {int(target_pages * 1500)} символов.
Формат: LaTeX (используй \\section{{{chapter_title}}} в начале).
НЕ используй длинные строки - разбивай на короткие (до 80 символов).
Можешь включить формулы, таблицы или рисунки где уместно.
Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно.
"""
    
    return await ask_assistant(order_id, prompt, model_name)


async def generate_subsections_content(
    order_id: int, 
    model_name: str, 
    chapter_title: str, 
    subsections: List[str], 
    target_pages: float,
    theme: str
) -> str:
    """
    Генерирует содержание подразделов для увеличения объема главы.
    
    Args:
        order_id: ID заказа
        model_name: Название модели GPT
        chapter_title: Название главы
        subsections: Список подразделов
        target_pages: Сколько страниц нужно добавить
        theme: Тема работы
    
    Returns:
        Содержание подразделов в формате LaTeX
    """
    if not subsections:
        # Если подразделы не указаны, просим GPT их придумать
        subsections_prompt = f"""
Предложи 2-3 подраздела для главы "{chapter_title}" в работе на тему "{theme}".
Ответь только названиями подразделов, каждый с новой строки, без нумерации.
"""
        subsections_text = await ask_assistant(order_id, subsections_prompt, model_name)
        subsections = [s.strip() for s in subsections_text.split('\n') if s.strip()]
    
    if not subsections:
        return ""
    
    pages_per_subsection = target_pages / len(subsections)
    subsections_content = ""
    
    for i, subsection in enumerate(subsections):
        subsection_prompt = f"""
Напиши подраздел "{subsection}" для главы "{chapter_title}" в работе на тему "{theme}".

ВАЖНО: Это подраздел, а НЕ отдельная глава!

Подраздел должен быть детальным и содержательным.
Объем: примерно {int(pages_per_subsection * 1500)} символов.

Формат: LaTeX
- ОБЯЗАТЕЛЬНО используй \\subsection{{{subsection}}} в начале (НЕ \\section!)
- НЕ используй длинные строки - разбивай на короткие (до 80 символов)
- Пиши академический текст с примерами и анализом
- Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно

Начни с команды \\subsection{{{subsection}}} и продолжи содержанием.
"""
        
        subsection_content = await ask_assistant(order_id, subsection_prompt, model_name)
        
        # Дополнительная проверка и исправление: заменяем \section на \subsection если GPT ошибся
        subsection_content = fix_section_commands(subsection_content, subsection)
        
        subsections_content += subsection_content + "\n\n"
    
    return subsections_content.strip()


async def generate_full_work_content_legacy(order_id: int, model_name: str, theme: str, pages: int, work_type: str) -> str:
    """
    Старый метод генерации полного содержания (fallback).
    
    Args:
        order_id: ID заказа
        model_name: Название модели GPT
        theme: Тема работы
        pages: Количество страниц
        work_type: Тип работы
    
    Returns:
        Полное содержание работы в формате LaTeX
    """
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
    
    return await ask_assistant(order_id, full_work_prompt, model_name)


def fix_section_commands(content: str, expected_subsection_title: str) -> str:
    """
    Исправляет неправильные команды LaTeX в подразделах.
    Заменяет \section на \subsection если GPT ошибся.
    
    Args:
        content: Содержание подраздела
        expected_subsection_title: Ожидаемое название подраздела
    
    Returns:
        Исправленное содержание
    """
    import re
    
    # Убираем лишние \newpage в начале подраздела
    content = re.sub(r'^\\newpage\s*', '', content.strip())
    
    # Ищем команды \section в начале содержания
    section_pattern = r'^\\section\{([^}]+)\}'
    match = re.search(section_pattern, content.strip(), re.MULTILINE)
    
    if match:
        try:
            # Проверяем, что группа существует
            if match.lastindex and match.lastindex >= 1:
                section_title = match.group(1)
                # Заменяем \section на \subsection
                content = re.sub(section_pattern, f'\\\\subsection{{{section_title}}}', content, count=1)
        except (IndexError, AttributeError):
            pass
    
    # Дополнительная проверка: если нет ни \section, ни \subsection в начале, добавляем \subsection
    if not re.search(r'^\\(sub)?section\{', content.strip(), re.MULTILINE):
        content = f"\\subsection{{{expected_subsection_title}}}\n\n{content}"
        print(f"Added missing \\subsection{{{expected_subsection_title}}}")
    
    return content


def _is_bibliography_chapter(chapter_title: str) -> bool:
    """
    Проверяет, является ли глава списком литературы.
    
    Args:
        chapter_title: Название главы
    
    Returns:
        True, если это список литературы
    """
    title_lower = chapter_title.lower()
    return any(keyword in title_lower for keyword in ['список', 'библиография', 'источник', 'литература'])