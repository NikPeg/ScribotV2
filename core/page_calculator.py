"""
Модуль для расчета количества страниц и управления объемом работы.
"""

import re

# Константы для расчета страниц
# Учитываем, что в LaTeX документе:
# - Титульный лист занимает ~1 страницу
# - Оглавление занимает ~0.5-1 страницу
# - Заголовки, пустые строки, форматирование уменьшают реальный объем текста на странице
# - Реальный объем текста на странице A4 с полями 3см/1.5см/2см/2см и полуторным интервалом ~1200-1300 символов
SYMBOLS_IN_PAGE = 1250  # Более реалистичное значение с учетом форматирования LaTeX

# Дополнительные страницы, которые занимают служебные элементы
TITLE_PAGE_PAGES = 1.0  # Титульный лист
TOC_PAGES_BASE = 0.5    # Базовое количество страниц для оглавления
TOC_PAGES_PER_CHAPTER = 0.05  # Дополнительные страницы оглавления на каждую главу


def count_pages_in_text(text: str) -> float:
    """
    Подсчитывает количество страниц в тексте на основе символов.
    Учитывает только содержание (без титульного листа и оглавления).
    
    Args:
        text: Текст для подсчета
    
    Returns:
        Количество страниц содержания (может быть дробным)
    """
    # Убираем LaTeX команды для более точного подсчета
    clean_text = remove_latex_commands(text)
    symbol_count = len(clean_text)
    return symbol_count / SYMBOLS_IN_PAGE


def count_total_pages_in_document(content_text: str, num_chapters: int = 0) -> float:
    """
    Подсчитывает общее количество страниц в полном LaTeX документе.
    Учитывает титульный лист, оглавление и содержание.
    
    Args:
        content_text: Текст содержания (без титульного листа и оглавления)
        num_chapters: Количество глав (для расчета размера оглавления)
    
    Returns:
        Общее количество страниц в докуменte
    """
    content_pages = count_pages_in_text(content_text)
    toc_pages = TOC_PAGES_BASE + (num_chapters * TOC_PAGES_PER_CHAPTER)
    return TITLE_PAGE_PAGES + toc_pages + content_pages


def calculate_content_pages_for_target(total_target_pages: int, num_chapters: int = 0) -> float:
    """
    Рассчитывает, сколько страниц содержания нужно сгенерировать,
    чтобы получить документ нужного объема с учетом титульного листа и оглавления.
    
    Args:
        total_target_pages: Общее целевое количество страниц в документе
        num_chapters: Количество глав (для расчета размера оглавления)
    
    Returns:
        Необходимое количество страниц содержания
    """
    toc_pages = TOC_PAGES_BASE + (num_chapters * TOC_PAGES_PER_CHAPTER)
    service_pages = TITLE_PAGE_PAGES + toc_pages
    return max(1.0, total_target_pages - service_pages)


def remove_latex_commands(text: str) -> str:
    """
    Убирает LaTeX команды из текста для подсчета символов.
    
    Args:
        text: Исходный текст с LaTeX командами
    
    Returns:
        Очищенный текст без команд
    """
    # Убираем команды типа \section{}, \subsection{} и т.д.
    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
    text = re.sub(r'\\[a-zA-Z]+\*?\{[^}]*\}', '', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r'\\\\', '\n', text)
    
    # Убираем лишние пробелы и переносы
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def _parse_chapter_title(line: str) -> str | None:
    """Парсит название главы из строки. Возвращает название или None если это не глава."""
    chapter_patterns = [
        (r'^(\d+)\.\s*(.+)$', 2),
        (r'^Глава\s*(\d+)\.?\s*(.+)$', 2),
        (r'^(\d+)\)\s*(.+)$', 2),
        (r'^[IVX]+\.\s*(.+)$', 1),
    ]
    
    for pattern, title_group in chapter_patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            try:
                if match.lastindex and title_group <= match.lastindex:
                    return match.group(title_group).strip()
                return re.sub(r'^[\d\w\.\)\s]+', '', line).strip()
            except (IndexError, AttributeError):
                return re.sub(r'^[\d\w\.\)\s]+', '', line).strip()
    
    return None


def _parse_subsection_title(line: str) -> str | None:
    """Парсит название подраздела из строки. Возвращает название или None если это не подраздел."""
    subsection_patterns = [
        r'^(\d+\.\d+)\s*(.+)$',
        r'^-\s*(.+)$',
        r'^\*\s*(.+)$',
    ]
    
    for pattern in subsection_patterns:
        match = re.match(pattern, line)
        if match:
            try:
                if match.lastindex:
                    subsection_title = match.group(match.lastindex).strip()
                else:
                    subsection_title = re.sub(r'^[-\*\d\.\s]+', '', line).strip()
                
                return subsection_title if subsection_title else None
            except (IndexError, AttributeError):
                subsection_title = re.sub(r'^[-\*\d\.\s]+', '', line).strip()
                return subsection_title if subsection_title else None
    
    return None


def parse_work_plan(plan_text: str) -> list[dict[str, str]]:
    """
    Парсит план работы и извлекает структуру глав.
    
    Args:
        plan_text: Текст плана работы от GPT
    
    Returns:
        Список словарей с информацией о главах
    """
    chapters = []
    lines = plan_text.split('\n')
    current_chapter = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        chapter_title = _parse_chapter_title(line)
        if chapter_title:
            if current_chapter:
                chapters.append(current_chapter)
            
            current_chapter = {
                'title': chapter_title,
                'subsections': []
            }
            continue
        
        if current_chapter:
            subsection_title = _parse_subsection_title(line)
            if subsection_title:
                current_chapter['subsections'].append(subsection_title)
    
    if current_chapter:
        chapters.append(current_chapter)
    
    return chapters


def calculate_pages_per_chapter(total_pages: int, chapters: list[dict]) -> dict[str, float]:
    """
    Рассчитывает количество страниц на каждую главу.
    
    Args:
        total_pages: Общее количество страниц
        chapters: Список глав из плана
    
    Returns:
        Словарь с количеством страниц для каждой главы
    """
    if not chapters:
        return {}
    
    # Базовое распределение страниц
    pages_per_chapter = {}
    
    # Особые главы с фиксированным объемом
    special_chapters = {
        'введение': 1.5,
        'заключение': 1.5,
        'список': 0.5,  # Список литературы
        'библиография': 0.5,
    }
    
    # Подсчитываем страницы для специальных глав
    special_pages = 0
    main_chapters = []
    
    for chapter in chapters:
        title_lower = chapter['title'].lower()
        is_special = False
        
        for special_key, pages in special_chapters.items():
            if special_key in title_lower:
                pages_per_chapter[chapter['title']] = pages
                special_pages += pages
                is_special = True
                break
        
        if not is_special:
            main_chapters.append(chapter)
    
    # Распределяем оставшиеся страницы между основными главами
    remaining_pages = total_pages - special_pages
    if main_chapters and remaining_pages > 0:
        pages_per_main_chapter = remaining_pages / len(main_chapters)
        for chapter in main_chapters:
            pages_per_chapter[chapter['title']] = pages_per_main_chapter
    
    return pages_per_chapter


def should_generate_subsections(current_pages: float, target_pages: float, threshold: float = 0.7) -> bool:
    """
    Определяет, нужно ли генерировать подразделы для достижения целевого объема.
    
    Args:
        current_pages: Текущее количество страниц
        target_pages: Целевое количество страниц
        threshold: Порог (если текущих страниц меньше threshold * target, генерируем подразделы)
    
    Returns:
        True, если нужно генерировать подразделы
    """
    return current_pages < (target_pages * threshold)


def is_chapter_complete(current_pages: float, target_pages: float, tolerance: float = 0.2) -> bool:
    """
    Определяет, завершена ли глава (достигнут ли целевой объем).
    
    Args:
        current_pages: Текущее количество страниц
        target_pages: Целевое количество страниц
        tolerance: Допустимое отклонение (20% по умолчанию)
    
    Returns:
        True, если глава завершена
    """
    min_pages = target_pages * (1 - tolerance)
    max_pages = target_pages * (1 + tolerance)
    return min_pages <= current_pages <= max_pages


def count_plan_items(chapters: list[dict]) -> int:
    """
    Подсчитывает общее количество пунктов в плане (глав + подразделов).
    
    Args:
        chapters: Список глав из плана
    
    Returns:
        Общее количество пунктов (глав + подразделов)
    """
    total_items = 0
    for chapter in chapters:
        total_items += 1  # Сама глава
        total_items += len(chapter.get('subsections', []))  # Подразделы
    return total_items


def validate_work_plan(plan_text: str, pages: int) -> tuple[bool, int]:
    """
    Валидирует план работы: проверяет, что количество пунктов достаточно.
    
    Args:
        plan_text: Текст плана работы
        pages: Целевое количество страниц
    
    Returns:
        Кортеж (is_valid, items_count):
        - is_valid: True, если план валиден (количество пунктов >= pages / 3)
        - items_count: Количество пунктов в плане
    """
    try:
        chapters = parse_work_plan(plan_text)
        items_count = count_plan_items(chapters)
        min_items = max(1, pages // 3)  # Минимум треть от числа страниц
        is_valid = items_count >= min_items
        return is_valid, items_count
    except Exception:
        return False, 0
