"""
Модуль для генерации содержания работ через GPT с контролем объема.
"""

import random
import re
from collections.abc import Callable
from dataclasses import dataclass

from aiogram import Bot

from core.latex_template import validate_latex_tags
from core.page_calculator import (
    calculate_content_pages_for_target,
    calculate_pages_per_chapter,
    count_pages_in_text,
    parse_work_plan,
    should_generate_subsections,
)
from db.database import get_order_info
from gpt.assistant import ask_assistant
from utils.admin_logger import send_admin_log


@dataclass
class WorkContentParams:
    """Параметры для генерации содержания работы."""
    order_id: int
    model_name: str
    theme: str
    pages: int
    work_type: str
    plan_text: str
    progress_callback: Callable | None = None
    bot: Bot | None = None


@dataclass
class ChapterContentParams:
    """Параметры для генерации содержания главы."""
    order_id: int
    model_name: str
    chapter_title: str
    theme: str
    target_pages: float
    work_type: str
    bot: Bot | None = None


@dataclass
class SubsectionsContentParams:
    """Параметры для генерации содержания подразделов."""
    order_id: int
    model_name: str
    chapter_title: str
    subsections: list[str]
    target_pages: float
    theme: str
    bot: Bot | None = None


@dataclass
class MainChaptersGenerationParams:
    """Параметры для генерации основных глав."""
    main_chapters: list[dict]
    order_id: int
    model_name: str
    theme: str
    work_type: str
    pages_per_chapter: dict[str, float]
    content_target_pages: float
    progress_callback: Callable | None = None
    bot: Bot | None = None


@dataclass
class BibliographyGenerationParams:
    """Параметры для генерации библиографии."""
    bibliography_chapter: dict | None
    order_id: int
    model_name: str
    theme: str
    work_type: str
    progress_callback: Callable | None = None
    bot: Bot | None = None


async def _send_validation_warning_to_admin(
    bot: Bot | None,
    order_id: int,
    chapter_title: str,
    error_msg: str,
    is_subsection: bool = False
) -> None:
    """
    Отправляет предупреждение администратору о проблемах с валидацией главы/подраздела.
    
    Args:
        bot: Экземпляр бота для отправки сообщения
        order_id: ID заказа
        chapter_title: Название главы или подраздела
        error_msg: Сообщение об ошибке валидации
        is_subsection: Флаг, указывающий что это подраздел
    """
    if not bot:
        print(f"WARNING: Не удалось отправить предупреждение администратору (bot=None). "
              f"Заказ #{order_id}, глава '{chapter_title}', ошибка: {error_msg}")
        return
    
    try:
        order_info = await get_order_info(order_id)
        if not order_info:
            return
        
        # Создаем фиктивного пользователя для лога
        class FakeUser:
            def __init__(self, user_id):
                self.id = user_id
                self.full_name = f"User {user_id}"
                self.username = None
        
        fake_user = FakeUser(order_info['user_id'])
        
        content_type = "подраздел" if is_subsection else "главу"
        warning_message = (
            f"⚠️ <b>Предупреждение: проблема с валидацией {content_type}</b>\n"
            f"  <b>Заказ:</b> #{order_id}\n"
            f"  <b>Тема:</b> {order_info['theme'][:100]}\n"
            f"  <b>{'Подраздел' if is_subsection else 'Глава'}:</b> {chapter_title[:100]}\n"
            f"  <b>Ошибка:</b> {error_msg[:200]}\n\n"
            f"<i>Генерация работы продолжается с невалидным контентом.</i>"
        )
        
        await send_admin_log(bot, fake_user, warning_message)
    except Exception as e:
        print(f"Failed to send validation warning to admin: {e}")


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


def _split_chapters(chapters: list[dict]) -> tuple[list[dict], dict | None]:
    """Разделяет главы на основные и библиографию."""
    main_chapters = []
    bibliography_chapter = None
    
    for chapter in chapters:
        if _is_bibliography_chapter(chapter['title']):
            bibliography_chapter = chapter
        else:
            main_chapters.append(chapter)
    
    return main_chapters, bibliography_chapter


async def _generate_main_chapters(params: MainChaptersGenerationParams) -> str:
    """Генерирует содержание основных глав."""
    full_content = ""
    total_pages_generated = 0.0
    
    for i, chapter in enumerate(params.main_chapters):
        chapter_title = chapter['title']
        target_pages = params.pages_per_chapter.get(chapter_title, 2.0)
        
        if params.progress_callback:
            progress = int((i / len(params.main_chapters)) * 90)
            await params.progress_callback(f"Генерирую главу: {chapter_title[:50]}...", progress)
        
        chapter_params = ChapterContentParams(
            order_id=params.order_id,
            model_name=params.model_name,
            chapter_title=chapter_title,
            theme=params.theme,
            target_pages=target_pages,
            work_type=params.work_type,
            bot=params.bot
        )
        chapter_content = await generate_chapter_content(chapter_params)
        
        current_chapter_pages = count_pages_in_text(chapter_content)
        
        if should_generate_subsections(current_chapter_pages, target_pages):
            subsections_params = SubsectionsContentParams(
                order_id=params.order_id,
                model_name=params.model_name,
                chapter_title=chapter_title,
                subsections=chapter['subsections'],
                target_pages=target_pages - current_chapter_pages,
                theme=params.theme,
                bot=params.bot
            )
            subsections_content = await generate_subsections_content(subsections_params)
            chapter_content += "\n\n" + subsections_content
            current_chapter_pages = count_pages_in_text(chapter_content)
        
        full_content += chapter_content + "\n\n\\newpage\n\n"
        total_pages_generated += current_chapter_pages
        
        if total_pages_generated >= params.content_target_pages * 1.15:
            break
    
    return full_content


async def _generate_bibliography(params: BibliographyGenerationParams) -> str:
    """Генерирует список источников."""
    if params.progress_callback:
        await params.progress_callback("Генерирую список источников...", 95)
    
    chapter_title = (
        params.bibliography_chapter['title'] if params.bibliography_chapter
        else "Список использованных источников"
    )
    
    bibliography_params = ChapterContentParams(
        order_id=params.order_id,
        model_name=params.model_name,
        chapter_title=chapter_title,
        theme=params.theme,
        target_pages=0.5,
        work_type=params.work_type,
        bot=params.bot
    )
    return await generate_chapter_content(bibliography_params)


async def generate_work_content_stepwise(params: WorkContentParams) -> str:
    """
    Генерирует содержание работы пошагово с контролем объема.
    
    Args:
        params: Параметры генерации содержания работы
    
    Returns:
        Полное содержание работы в формате LaTeX
    """
    order_id = params.order_id
    model_name = params.model_name
    theme = params.theme
    pages = params.pages
    work_type = params.work_type
    plan_text = params.plan_text
    progress_callback = params.progress_callback
    bot = params.bot
    
    try:
        chapters = parse_work_plan(plan_text)
    except Exception:
        return await generate_full_work_content_legacy(order_id, model_name, theme, pages, work_type)
    
    if not chapters:
        return await generate_full_work_content_legacy(order_id, model_name, theme, pages, work_type)
    
    main_chapters, bibliography_chapter = _split_chapters(chapters)
    
    content_target_pages = calculate_content_pages_for_target(pages, len(main_chapters))
    pages_per_chapter = calculate_pages_per_chapter(content_target_pages - 0.5, main_chapters)
    
    main_chapters_params = MainChaptersGenerationParams(
        main_chapters=main_chapters,
        order_id=order_id,
        model_name=model_name,
        theme=theme,
        work_type=work_type,
        pages_per_chapter=pages_per_chapter,
        content_target_pages=content_target_pages,
        progress_callback=progress_callback,
        bot=bot
    )
    main_content = await _generate_main_chapters(main_chapters_params)
    
    bibliography_params = BibliographyGenerationParams(
        bibliography_chapter=bibliography_chapter,
        order_id=order_id,
        model_name=model_name,
        theme=theme,
        work_type=work_type,
        progress_callback=progress_callback,
        bot=bot
    )
    bibliography_content = await _generate_bibliography(bibliography_params)
    
    full_content = (main_content + bibliography_content).strip()
    
    # Исправляем ссылки на источники
    return fix_citations_in_work_content(full_content)


async def generate_chapter_content(params: ChapterContentParams) -> str:
    """
    Генерирует содержание одной главы с валидацией LaTeX тегов.
    При обнаружении незакрытых тегов перегенерирует главу (до 3 попыток).
    Если после всех попыток глава невалидна, отправляет предупреждение администратору
    и продолжает генерацию с невалидным контентом.
    
    Args:
        params: Параметры генерации содержания главы
    
    Returns:
        Содержание главы в формате LaTeX (может быть невалидным)
    """
    order_id = params.order_id
    model_name = params.model_name
    chapter_title = params.chapter_title
    theme = params.theme
    target_pages = params.target_pages
    work_type = params.work_type
    bot = params.bot
    
    MAX_ATTEMPTS = 3
    
    # Определяем тип главы для специальной обработки
    title_lower = chapter_title.lower()
    
    # Инициализируем переменные для хранения последнего контента и ошибки
    last_content = None
    last_error_msg = None
    
    for attempt in range(MAX_ATTEMPTS):
        if 'введение' in title_lower:
            prompt = f"""
Напиши введение для {work_type.lower()} на тему "{theme}".

Введение должно содержать:
- Актуальность темы
- Цель и задачи работы
- Объект и предмет исследования
- Методы исследования
- Структуру работы

Объем: примерно {int(target_pages * 1250)} символов.
Формат: LaTeX (используй \\section{{Введение}} в начале).
НЕ используй длинные строки - разбивай на короткие (до 80 символов).
Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно, но умеренно - по несколько ссылок на страницу.
"""
        
        elif 'заключение' in title_lower:
            prompt = f"""
Напиши заключение для {work_type.lower()} на тему "{theme}".

Заключение должно содержать:
- Краткие выводы по каждой главе
- Достижение поставленных целей и задач
- Практическую значимость результатов
- Перспективы дальнейших исследований

Объем: примерно {int(target_pages * 1250)} символов.
Формат: LaTeX (используй \\section{{Заключение}} в начале).
НЕ используй длинные строки - разбивай на короткие (до 80 символов).
Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно, но умеренно - по несколько ссылок на страницу.
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

Объем: примерно {int(target_pages * 1250)} символов.
Формат: LaTeX (используй \\section{{{chapter_title}}} в начале).
НЕ используй длинные строки - разбивай на короткие (до 80 символов).
Можешь включить формулы, таблицы или рисунки где уместно.
Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно, но умеренно - по несколько ссылок на страницу.
"""
        
        chapter_content = await ask_assistant(order_id, prompt, model_name)
        
        # Валидируем LaTeX теги
        is_valid, error_msg = validate_latex_tags(chapter_content)
        
        if is_valid:
            return chapter_content
        
        # Сохраняем последний контент и ошибку
        last_content = chapter_content
        last_error_msg = error_msg
        
        # Если невалиден и это не последняя попытка - перегенерируем
        if attempt < MAX_ATTEMPTS - 1:
            print(f"Глава '{chapter_title}': попытка {attempt + 1} невалидна - {error_msg}. Перегенерирую...")
            continue
    
    # Если все попытки исчерпаны - отправляем предупреждение администратору и продолжаем
    error_details = (
        f"Не удалось сгенерировать валидную главу '{chapter_title}' после {MAX_ATTEMPTS} попыток. "
        f"Последняя ошибка: {last_error_msg}"
    )
    
    print(f"WARNING: {error_details}. Продолжаю генерацию с невалидным контентом.")
    
    # Отправляем предупреждение администратору
    await _send_validation_warning_to_admin(bot, order_id, chapter_title, last_error_msg or "Неизвестная ошибка")
    
    # Возвращаем последний сгенерированный контент (даже если он невалиден)
    return last_content or ""


async def generate_subsections_content(params: SubsectionsContentParams) -> str:
    """
    Генерирует содержание подразделов для увеличения объема главы.
    Валидирует LaTeX теги и перегенерирует при необходимости (до 3 попыток).
    Если после всех попыток подраздел невалиден, отправляет предупреждение администратору
    и продолжает генерацию с невалидным контентом.
    
    Args:
        params: Параметры генерации содержания подразделов
    
    Returns:
        Содержание подразделов в формате LaTeX (может быть невалидным)
    """
    order_id = params.order_id
    model_name = params.model_name
    chapter_title = params.chapter_title
    subsections = params.subsections
    target_pages = params.target_pages
    theme = params.theme
    bot = params.bot
    MAX_ATTEMPTS = 3
    
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
    
    for _i, subsection in enumerate(subsections):
        subsection_content = None
        last_error_msg = None
        is_valid = False
        
        for attempt in range(MAX_ATTEMPTS):
            subsection_prompt = f"""
Напиши подраздел "{subsection}" для главы "{chapter_title}" в работе на тему "{theme}".

ВАЖНО: Это подраздел, а НЕ отдельная глава!

Подраздел должен быть детальным и содержательным.
Объем: примерно {int(pages_per_subsection * 1250)} символов.

Формат: LaTeX
- ОБЯЗАТЕЛЬНО используй \\subsection{{{subsection}}} в начале (НЕ \\section!)
- НЕ используй длинные строки - разбивай на короткие (до 80 символов)
- Пиши академический текст с примерами и анализом
- Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно, но умеренно - по несколько ссылок на страницу

Начни с команды \\subsection{{{subsection}}} и продолжи содержанием.
"""
            
            subsection_content = await ask_assistant(order_id, subsection_prompt, model_name)
            
            # Дополнительная проверка и исправление: заменяем \section на \subsection если GPT ошибся
            subsection_content = fix_section_commands(subsection_content, subsection)
            
            # Валидируем LaTeX теги
            is_valid, error_msg = validate_latex_tags(subsection_content)
            
            if is_valid:
                break
            
            # Сохраняем последнюю ошибку
            last_error_msg = error_msg
            
            # Если невалиден и это не последняя попытка - перегенерируем
            if attempt < MAX_ATTEMPTS - 1:
                print(f"Подраздел '{subsection}': попытка {attempt + 1} невалидна - {error_msg}. Перегенерирую...")
                continue
        
        # Если подраздел невалиден после всех попыток - отправляем предупреждение и продолжаем
        if subsection_content and not is_valid:
            error_details = (
                f"Не удалось сгенерировать валидный подраздел '{subsection}' для главы '{chapter_title}' "
                f"после {MAX_ATTEMPTS} попыток. Последняя ошибка: {last_error_msg}"
            )
            print(f"WARNING: {error_details}. Продолжаю генерацию с невалидным контентом.")
            
            # Отправляем предупреждение администратору
            full_subsection_title = f"{chapter_title} / {subsection}"
            await _send_validation_warning_to_admin(
                bot, order_id, full_subsection_title, last_error_msg or "Неизвестная ошибка", is_subsection=True
            )
        
        # Добавляем контент подраздела (даже если он невалиден)
        if subsection_content:
            subsections_content += subsection_content + "\n\n"
    
    return subsections_content.strip()


async def generate_simple_work_content(order_id: int, model_name: str, theme: str, work_type: str) -> str:
    """
    Генерирует простую работу (1-2 страницы) без плана и оглавления.
    Генерирует текст работы одним запросом и список источников другим.
    
    Args:
        order_id: ID заказа
        model_name: Название модели GPT
        theme: Тема работы
        work_type: Тип работы
    
    Returns:
        Полное содержание работы в формате LaTeX (текст + список источников)
    """
    # Генерируем основной текст работы
    main_content_prompt = f"""
Напиши {work_type.lower()} на тему "{theme}" объемом примерно 1-2 страницы.

Текст должен быть кратким, но содержательным и включать:
- Краткое введение (2-3 абзаца)
- Основную часть с анализом темы (3-4 абзаца)
- Краткое заключение (1-2 абзаца)

ВАЖНЫЕ требования к форматированию:
- Текст должен быть в формате LaTeX (без преамбулы и \\begin{{document}})
- Используй команду \\section{{Введение}} в начале
- Используй команду \\section{{Основная часть}} для основной части
- Используй команду \\section{{Заключение}} для заключения
- НЕ используй длинные строки текста - разбивай абзацы на короткие строки (максимум 80 символов)
- После каждого предложения делай перенос строки
- Текст должен быть академическим
- Используй ссылки на источники через команду \\cite{{source1}}, \\cite{{source2}} и т.д. где уместно, но умеренно - по несколько ссылок на страницу

Начни прямо с введения:
"""
    
    main_content = await ask_assistant(order_id, main_content_prompt, model_name)
    
    # Генерируем список источников отдельно
    bibliography_prompt = f"""
Создай список использованных источников для {work_type.lower()} на тему "{theme}".

Включи 8-12 источников:
- Научные статьи
- Монографии
- Учебники
- Интернет-ресурсы

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
    
    bibliography = await ask_assistant(order_id, bibliography_prompt, model_name)
    
    # Объединяем основной текст и список источников
    full_content = main_content + "\n\n" + bibliography
    
    # Исправляем ссылки на источники
    return fix_citations_in_work_content(full_content)


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
    
    full_content = await ask_assistant(order_id, full_work_prompt, model_name)
    
    # Исправляем ссылки на источники
    return fix_citations_in_work_content(full_content)


def fix_section_commands(content: str, expected_subsection_title: str) -> str:
    r"""
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


def _extract_source_count_from_bibliography(bibliography_content: str) -> int:
    """
    Извлекает количество источников из библиографии.
    
    Ищет все \\bibitem{source?} и возвращает максимальный номер источника.
    
    Args:
        bibliography_content: Содержимое раздела библиографии
    
    Returns:
        Количество источников (максимальный номер)
    """
    # Ищем все \bibitem{source?} где ? - число
    pattern = r'\\bibitem\{source(\d+)\}'
    matches = re.findall(pattern, bibliography_content)
    
    if not matches:
        return 0
    
    # Находим максимальный номер
    return max(int(num) for num in matches)


def _replace_citations_in_content(content: str, bibliography_content: str) -> str:
    """
    Заменяет все \\cite{???} на правильные номера источников из библиографии.
    
    Сначала идет по порядку (1, 2, 3...), потом выбирает рандомно из всех источников.
    Не трогает уже правильные ссылки вида \\cite{source?}.
    
    Args:
        content: Основной текст работы (без библиографии)
        bibliography_content: Содержимое раздела библиографии
    
    Returns:
        Текст с замененными ссылками на источники
    """
    # Извлекаем количество источников
    source_count = _extract_source_count_from_bibliography(bibliography_content)
    
    if source_count == 0:
        # Если источников нет, просто удаляем все \cite{???}, кроме уже правильных
        # Удаляем только те, что не соответствуют формату source?
        return re.sub(r'\\cite\{(?!source\d+\})[^}]+\}', '', content)
    
    # Находим все \cite{???} в тексте, но пропускаем уже правильные \cite{source?}
    # Ищем только те, что не соответствуют формату source?
    cite_pattern = r'\\cite\{(?!source\d+\})[^}]+\}'
    citations = re.findall(cite_pattern, content)
    
    if not citations:
        return content
    
    # Сначала идем по порядку (1, 2, 3...)
    sequential_index = 0
    
    def replace_citation(match):  # noqa: ARG001
        nonlocal sequential_index
        if sequential_index < source_count:
            # Используем последовательный номер
            source_num = sequential_index + 1
            sequential_index += 1
        else:
            # После последовательных - выбираем рандомно
            source_num = random.randint(1, source_count)
        
        return f'\\cite{{source{source_num}}}'
    
    # Заменяем только неправильные ссылки
    return re.sub(cite_pattern, replace_citation, content)


def fix_citations_in_work_content(full_content: str) -> str:
    """
    Исправляет ссылки на источники в полном тексте работы.
    
    Разделяет текст на основной контент и библиографию,
    затем заменяет все \\cite{???} на правильные номера источников.
    
    Args:
        full_content: Полное содержание работы (текст + библиография)
    
    Returns:
        Содержание с исправленными ссылками
    """
    # Ищем раздел библиографии
    bibliography_patterns = [
        r'(.*?)(\\section\{[^}]*(?:Список|список)[^}]*(?:литературы|источников|использованных)[^}]*\}.*)',
        r'(.*?)(\\section\*\{[^}]*(?:Список|список)[^}]*(?:литературы|источников|использованных)[^}]*\}.*)',
        r'(.*?)(\\chapter\{[^}]*(?:Список|список)[^}]*(?:литературы|источников|использованных)[^}]*\}.*)'
    ]
    
    main_content = full_content
    bibliography_content = ""
    
    for pattern in bibliography_patterns:
        match = re.search(pattern, full_content, re.DOTALL | re.IGNORECASE)
        if match:
            main_content = match.group(1)
            bibliography_content = match.group(2)
            break
    
    if not bibliography_content:
        # Если библиография не найдена, просто возвращаем исходный текст
        return full_content
    
    # Заменяем ссылки в основном контенте
    fixed_main_content = _replace_citations_in_content(main_content, bibliography_content)
    
    # Объединяем исправленный основной контент и библиографию
    return fixed_main_content + bibliography_content
