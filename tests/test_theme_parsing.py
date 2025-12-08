"""
Тесты для парсинга многострочной темы работы с разделами
"""
import os
import sys

# Добавляем корневую директорию проекта в путь
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from core.content_generator import parse_theme_with_sections


def test_parse_simple_theme():
    """Тест: парсинг простой однострочной темы"""
    theme_text = "Организация торгово технологического процесса в розничных торговых предприятиях"
    theme, sections = parse_theme_with_sections(theme_text)
    
    assert theme == "Организация торгово технологического процесса в розничных торговых предприятиях"
    assert sections == []


def test_parse_theme_with_chapters():
    """Тест: парсинг темы с главами (пример пользователя)"""
    theme_text = """Организация торгово технологического процесса в розничных торговых предприятиях

Курсовая работа

Содержание работы.

Глава 1. Теоретико методологические аспекты торгово технологического процесса в магазине

1.1 содержание торгово технологического процесса в розничном магазине

1.2 организация и технология операций по поступлению товаров на предприятия розничной торговли

1.3 технология хранения и допродажной подготовки товаров

Глава 2. Пути совершенствования технологического процесса в розничном торговом предприятии

2.1 рекомендации по оптимизации построения торгово технологического процесса в магазине

2.2 оценка эффективности предложенных мероприятий по оптимизации"""
    
    theme, sections = parse_theme_with_sections(theme_text)
    
    # Первая строка должна быть темой
    assert theme == "Организация торгово технологического процесса в розничных торговых предприятиях"
    
    # Должны быть извлечены разделы с подразделами
    assert len(sections) >= 2
    
    # Проверяем структуру: sections - это список словарей
    assert isinstance(sections, list)
    assert all(isinstance(s, dict) for s in sections)
    assert all('title' in s and 'subsections' in s for s in sections)
    
    # Проверяем, что "Глава 1" и "Глава 2" присутствуют в разделах
    section_titles = [s['title'].lower() for s in sections]
    assert any("теоретико методологические" in s or "глава 1" in s for s in section_titles)
    assert any("пути совершенствования" in s or "глава 2" in s for s in section_titles)
    
    # Проверяем, что подразделы сохранены
    first_section = next((s for s in sections if "теоретико" in s['title'].lower() or "глава 1" in s['title'].lower()), None)
    assert first_section is not None
    assert len(first_section['subsections']) == 3
    assert "содержание торгово технологического процесса" in first_section['subsections'][0].lower()
    
    second_section = next((s for s in sections if "пути совершенствования" in s['title'].lower() or "глава 2" in s['title'].lower()), None)
    assert second_section is not None
    assert len(second_section['subsections']) == 2


def test_parse_theme_with_more_than_3_sections():
    """Тест: парсинг темы с более чем 3 разделами (должны использоваться напрямую)"""
    theme_text = """Тема работы

Глава 1. Первая глава
Глава 2. Вторая глава
Глава 3. Третья глава
Глава 4. Четвертая глава
Глава 5. Пятая глава"""
    
    theme, sections = parse_theme_with_sections(theme_text)
    
    assert theme == "Тема работы"
    assert len(sections) == 5
    assert isinstance(sections, list)
    assert all(isinstance(s, dict) for s in sections)
    assert "Первая глава" in sections[0]['title'] or "Глава 1" in sections[0]['title']
    assert "Вторая глава" in sections[1]['title'] or "Глава 2" in sections[1]['title']
    assert "Третья глава" in sections[2]['title'] or "Глава 3" in sections[2]['title']
    assert "Четвертая глава" in sections[3]['title'] or "Глава 4" in sections[3]['title']
    assert "Пятая глава" in sections[4]['title'] or "Глава 5" in sections[4]['title']
    # У всех разделов должны быть пустые списки подразделов
    assert all(len(s['subsections']) == 0 for s in sections)


def test_parse_theme_with_less_than_3_sections():
    """Тест: парсинг темы с менее чем 3 разделами (нужно просить подразделы)"""
    theme_text = """Тема работы

Глава 1. Первая глава
Глава 2. Вторая глава"""
    
    theme, sections = parse_theme_with_sections(theme_text)
    
    assert theme == "Тема работы"
    assert len(sections) == 2
    assert isinstance(sections, list)
    assert all(isinstance(s, dict) for s in sections)
    assert "Первая глава" in sections[0]['title'] or "Глава 1" in sections[0]['title']
    assert "Вторая глава" in sections[1]['title'] or "Глава 2" in sections[1]['title']
    # У всех разделов должны быть пустые списки подразделов
    assert all(len(s['subsections']) == 0 for s in sections)


def test_parse_theme_with_subsections_ignored():
    """Тест: подразделы должны сохраняться при парсинге"""
    theme_text = """Тема работы

Глава 1. Первая глава
1.1 Первый подраздел
1.2 Второй подраздел
Глава 2. Вторая глава
2.1 Третий подраздел"""
    
    theme, sections = parse_theme_with_sections(theme_text)
    
    assert theme == "Тема работы"
    # Должны быть 2 раздела с подразделами
    assert len(sections) == 2
    assert isinstance(sections, list)
    assert all(isinstance(s, dict) for s in sections)
    assert "Первая глава" in sections[0]['title'] or "Глава 1" in sections[0]['title']
    assert "Вторая глава" in sections[1]['title'] or "Глава 2" in sections[1]['title']
    
    # Подразделы должны быть сохранены
    assert len(sections[0]['subsections']) == 2
    assert "Первый подраздел" in sections[0]['subsections'][0]
    assert "Второй подраздел" in sections[0]['subsections'][1]
    
    assert len(sections[1]['subsections']) == 1
    assert "Третий подраздел" in sections[1]['subsections'][0]


def test_parse_theme_with_numbered_sections():
    """Тест: парсинг темы с нумерованными разделами (без слова 'Глава')"""
    theme_text = """Тема работы

1. Первый раздел
2. Второй раздел
3. Третий раздел
4. Четвертый раздел"""
    
    theme, sections = parse_theme_with_sections(theme_text)
    
    assert theme == "Тема работы"
    assert len(sections) == 4
    assert isinstance(sections, list)
    assert all(isinstance(s, dict) for s in sections)
    assert "Первый раздел" in sections[0]['title']
    assert "Второй раздел" in sections[1]['title']
    assert "Третий раздел" in sections[2]['title']
    assert "Четвертый раздел" in sections[3]['title']
    assert all(len(s['subsections']) == 0 for s in sections)


def test_parse_theme_empty_lines_ignored():
    """Тест: пустые строки должны игнорироваться"""
    theme_text = """Тема работы


Глава 1. Первая глава


Глава 2. Вторая глава


"""
    
    theme, sections = parse_theme_with_sections(theme_text)
    
    assert theme == "Тема работы"
    assert len(sections) == 2
    assert isinstance(sections, list)
    assert all(isinstance(s, dict) for s in sections)
    assert "Первая глава" in sections[0]['title'] or "Глава 1" in sections[0]['title']
    assert "Вторая глава" in sections[1]['title'] or "Глава 2" in sections[1]['title']


def test_parse_theme_mixed_format():
    """Тест: парсинг темы со смешанным форматом (Глава и нумерация)"""
    theme_text = """Тема работы

Глава 1. Первая глава
2. Вторая глава
Раздел 3. Третий раздел"""
    
    theme, sections = parse_theme_with_sections(theme_text)
    
    assert theme == "Тема работы"
    assert len(sections) == 3
    assert isinstance(sections, list)
    assert all(isinstance(s, dict) for s in sections)
    assert "Первая глава" in sections[0]['title'] or "Глава 1" in sections[0]['title']
    assert "Вторая глава" in sections[1]['title']
    assert "Третий раздел" in sections[2]['title'] or "Раздел 3" in sections[2]['title']


def test_parse_theme_exactly_3_sections():
    """Тест: парсинг темы с ровно 3 разделами (граничный случай)"""
    theme_text = """Тема работы

Глава 1. Первая глава
Глава 2. Вторая глава
Глава 3. Третья глава"""
    
    theme, sections = parse_theme_with_sections(theme_text)
    
    assert theme == "Тема работы"
    assert len(sections) == 3
    assert isinstance(sections, list)
    assert all(isinstance(s, dict) for s in sections)
    # При 3 разделах (не больше 3) должна использоваться логика запроса подразделов
    assert "Первая глава" in sections[0]['title'] or "Глава 1" in sections[0]['title']
    assert "Вторая глава" in sections[1]['title'] or "Глава 2" in sections[1]['title']
    assert "Третья глава" in sections[2]['title'] or "Глава 3" in sections[2]['title']
    assert all(len(s['subsections']) == 0 for s in sections)

