"""
Модуль для расчета количества страниц и управления объемом работы.
"""

import re
from typing import List, Dict, Tuple


# Константы для расчета страниц
SYMBOLS_IN_PAGE = 2500


def count_pages_in_text(text: str) -> float:
    """
    Подсчитывает количество страниц в тексте на основе символов.
    
    Args:
        text: Текст для подсчета
    
    Returns:
        Количество страниц (может быть дробным)
    """
    # Убираем LaTeX команды для более точного подсчета
    clean_text = remove_latex_commands(text)
    symbol_count = len(clean_text)
    return symbol_count / SYMBOLS_IN_PAGE


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


def parse_work_plan(plan_text: str) -> List[Dict[str, str]]:
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
            
        # Ищем главы (различные форматы)
        chapter_patterns = [
            (r'^(\d+)\.\s*(.+)$', 2),  # "1. Введение" - название во 2-й группе
            (r'^Глава\s*(\d+)\.?\s*(.+)$', 2),  # "Глава 1. Название" - название во 2-й группе
            (r'^(\d+)\)\s*(.+)$', 2),  # "1) Введение" - название во 2-й группе
            (r'^[IVX]+\.\s*(.+)$', 1),  # "I. Введение" - название в 1-й группе
        ]
        
        chapter_found = False
        for pattern, title_group in chapter_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                if current_chapter:
                    chapters.append(current_chapter)
                
                try:
                    chapter_title = match.group(title_group).strip()
                except IndexError:
                    # Если группа не найдена, берем всю строку без номера
                    chapter_title = re.sub(r'^[\d\w\.\)\s]+', '', line).strip()
                
                current_chapter = {
                    'title': chapter_title,
                    'subsections': []
                }
                chapter_found = True
                break
        
        # Если не нашли главу, ищем подразделы
        if not chapter_found and current_chapter:
            subsection_patterns = [
                r'^(\d+\.\d+)\s*(.+)$',  # "1.1 Подраздел"
                r'^-\s*(.+)$',  # "- Подраздел"
                r'^\*\s*(.+)$',  # "* Подраздел"
            ]
            
            for pattern in subsection_patterns:
                match = re.match(pattern, line)
                if match:
                    subsection_title = match.group(-1).strip()
                    current_chapter['subsections'].append(subsection_title)
                    break
    
    # Добавляем последнюю главу
    if current_chapter:
        chapters.append(current_chapter)
    
    return chapters


def calculate_pages_per_chapter(total_pages: int, chapters: List[Dict]) -> Dict[str, float]:
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