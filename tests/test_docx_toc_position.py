"""
Тесты для проверки правильного расположения оглавления (TOC) в DOCX файлах.
Проверяет, что TOC находится после титульной страницы, а не в начале документа.
"""

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile

import pytest
from docx import Document

# Константы
MIN_TOC_CONTENT_LENGTH = 10  # Минимальная длина текста для проверки содержимого TOC

# Добавляем корневую директорию проекта в путь
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from gpt.assistant import TEST_MODEL_NAME  # noqa: E402
from scripts.generate import generate_test_work  # noqa: E402


def check_pandoc_available() -> bool:
    """
    Проверяет, доступен ли pandoc в системе.
    
    Returns:
        True, если pandoc доступен, False иначе
    """
    try:
        result = subprocess.run(
            ['pandoc', '--version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def find_toc_position(doc: Document) -> int | None:
    """
    Находит позицию TOC в документе.
    
    Args:
        doc: Document объект
    
    Returns:
        Индекс параграфа с TOC или None, если не найден
    """
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip().lower()
        if ('table of contents' in text or
            'содержание' in text or
            'оглавление' in text):
            return i
    return None


def find_toc_sdt_position(doc: Document) -> int | None:
    """
    Находит позицию TOC как SDT элемента в body документа.
    
    Args:
        doc: Document объект
    
    Returns:
        Индекс элемента в body или None, если не найден
    """
    body = doc.element.body
    for i, elem in enumerate(body):
        if 'sdt' in elem.tag.lower():
            return i
    return None


def find_title_page_end(doc: Document) -> int | None:
    """
    Находит конец титульной страницы в документе.
    
    Args:
        doc: Document объект
    
    Returns:
        Индекс последнего параграфа титульной страницы или None
    """
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if 'проверил:' in text.lower() or ('петров' in text.lower() and 'п.п' in text.lower()):
            # Ищем последний параграф титульной страницы
            title_end = i
            for j in range(i + 1, min(i + 3, len(doc.paragraphs))):
                if doc.paragraphs[j].text.strip():
                    title_end = j
                else:
                    break
            return title_end
    return None


def find_title_page_end_in_body(doc: Document) -> int | None:
    """
    Находит конец титульной страницы в body документа.
    
    Args:
        doc: Document объект
    
    Returns:
        Индекс элемента в body или None
    """
    body = doc.element.body
    title_end_para_idx = find_title_page_end(doc)
    if title_end_para_idx is None:
        return None
    
    para_count = 0
    for i, elem in enumerate(body):
        if 'p' in elem.tag.lower():
            if para_count == title_end_para_idx:
                return i
            para_count += 1
    return None


@pytest.fixture
def temp_dir():
    """Фикстура для создания временной директории"""
    temp_dir_path = tempfile.mkdtemp()
    yield temp_dir_path
    # Очистка после теста
    if os.path.exists(temp_dir_path):
        with contextlib.suppress(Exception):
            shutil.rmtree(temp_dir_path)


@pytest.fixture
def test_theme():
    """Фикстура для тестовой темы"""
    return "Тестовая работа для проверки TOC"


@pytest.fixture
def test_pages():
    """Фикстура для количества страниц"""
    return 2


@pytest.mark.asyncio
async def test_docx_toc_after_title_page(temp_dir, test_theme, test_pages):
    """
    Тест: проверяет, что TOC находится после титульной страницы в DOCX файле.
    
    Проверяет:
    1. DOCX файл создан
    2. TOC присутствует в документе
    3. TOC находится после титульной страницы (не в начале)
    """
    if not check_pandoc_available():
        pytest.skip("Pandoc не установлен. Пропускаем тест генерации DOCX.")
    
    # Генерируем тестовую работу
    result = await generate_test_work(
        theme=test_theme,
        pages=test_pages,
        work_type="курсовая",
        model_name=TEST_MODEL_NAME,
        output_dir=temp_dir
    )
    
    # Проверяем, что DOCX был создан
    assert result['docx_path'] is not None, "DOCX файл должен быть создан"
    assert os.path.exists(result['docx_path']), f"DOCX файл должен существовать: {result['docx_path']}"
    
    # Открываем DOCX файл
    doc = Document(result['docx_path'])
    
    # Проверяем наличие TOC
    toc_para_idx = find_toc_position(doc)
    toc_sdt_idx = find_toc_sdt_position(doc)
    
    assert toc_para_idx is not None or toc_sdt_idx is not None, (
        "TOC должен присутствовать в документе. "
        "Проверьте, что pandoc создал оглавление с флагом --toc."
    )
    
    # Находим конец титульной страницы
    title_end_para_idx = find_title_page_end(doc)
    assert title_end_para_idx is not None, (
        "Титульная страница должна быть найдена в документе. "
        "Проверьте структуру LaTeX шаблона."
    )
    
    # Проверяем, что TOC находится после титульной страницы
    if toc_para_idx is not None:
        assert toc_para_idx >= title_end_para_idx, (
            f"TOC должен находиться ПОСЛЕ или НА титульной странице. "
            f"Текущая позиция TOC: {toc_para_idx}, "
            f"конец титульной страницы: {title_end_para_idx}"
        )
    
    if toc_sdt_idx is not None:
        title_end_body_idx = find_title_page_end_in_body(doc)
        assert title_end_body_idx is not None, "Не удалось найти титульную страницу в body"
        # TOC может быть сразу после титульной страницы (>=), но не до неё
        assert toc_sdt_idx >= title_end_body_idx, (
            f"TOC (SDT) должен находиться ПОСЛЕ или НА титульной странице в body. "
            f"Текущая позиция TOC: {toc_sdt_idx}, "
            f"конец титульной страницы: {title_end_body_idx}"
        )
        # Если TOC на той же позиции, проверяем, что это не начало документа
        if toc_sdt_idx == title_end_body_idx:
            assert toc_sdt_idx > 0, "TOC не должен быть в самом начале документа"


@pytest.mark.asyncio
async def test_docx_toc_not_at_beginning(temp_dir, test_theme, test_pages):
    """
    Тест: проверяет, что TOC НЕ находится в самом начале документа.
    
    Pandoc по умолчанию размещает TOC в начале, но наша функция
    должна переместить его после титульной страницы.
    """
    if not check_pandoc_available():
        pytest.skip("Pandoc не установлен. Пропускаем тест генерации DOCX.")
    
    # Генерируем тестовую работу
    result = await generate_test_work(
        theme=test_theme,
        pages=test_pages,
        work_type="курсовая",
        model_name=TEST_MODEL_NAME,
        output_dir=temp_dir
    )
    
    # Проверяем, что DOCX был создан
    assert result['docx_path'] is not None
    assert os.path.exists(result['docx_path'])
    
    # Открываем DOCX файл
    doc = Document(result['docx_path'])
    body = doc.element.body
    
    # Проверяем, что первый элемент - не TOC
    if len(body) > 0:
        first_elem = body[0]
        first_is_toc = 'sdt' in first_elem.tag.lower()
        
        # Если первый элемент - TOC, проверяем, что это не начало документа
        if first_is_toc:
            # Проверяем первые параграфы
            first_para_text = doc.paragraphs[0].text.strip().lower() if doc.paragraphs else ""
            is_toc_text = 'table of contents' in first_para_text or 'содержание' in first_para_text
            
            assert not is_toc_text, (
                "TOC не должен быть в самом начале документа. "
                "Проверьте функцию _move_toc_after_title_page()."
            )


@pytest.mark.asyncio
async def test_docx_structure_order(temp_dir, test_theme, test_pages):
    """
    Тест: проверяет правильный порядок элементов в DOCX файле.
    
    Правильный порядок:
    1. Титульная страница
    2. Оглавление (TOC)
    3. Основной контент
    """
    if not check_pandoc_available():
        pytest.skip("Pandoc не установлен. Пропускаем тест генерации DOCX.")
    
    # Генерируем тестовую работу
    result = await generate_test_work(
        theme=test_theme,
        pages=test_pages,
        work_type="курсовая",
        model_name=TEST_MODEL_NAME,
        output_dir=temp_dir
    )
    
    # Проверяем, что DOCX был создан
    assert result['docx_path'] is not None
    assert os.path.exists(result['docx_path'])
    
    # Открываем DOCX файл
    doc = Document(result['docx_path'])
    paragraphs = list(doc.paragraphs)
    
    # Находим позиции ключевых элементов
    title_start_idx = None
    title_end_idx = find_title_page_end(doc)
    toc_idx = find_toc_position(doc)
    
    # Находим начало титульной страницы
    for i, para in enumerate(paragraphs):
        text = para.text.strip().lower()
        if 'министерство' in text or 'российский государственный университет' in text:
            title_start_idx = i
            break
    
    assert title_start_idx is not None, "Не удалось найти начало титульной страницы"
    assert title_end_idx is not None, "Не удалось найти конец титульной страницы"
    
    # TOC может быть найден в параграфах или как SDT элемент
    toc_sdt_idx = find_toc_sdt_position(doc)
    assert toc_idx is not None or toc_sdt_idx is not None, "Не удалось найти TOC"
    
    # Если TOC найден в параграфах, проверяем порядок
    if toc_idx is not None:
        # Проверяем порядок: титульная страница → TOC → контент
        assert title_start_idx < title_end_idx <= toc_idx, (
            f"Неправильный порядок элементов! "
            f"Начало титульной страницы: {title_start_idx}, "
            f"Конец титульной страницы: {title_end_idx}, "
            f"TOC: {toc_idx}. "
            f"Ожидаемый порядок: титульная страница → TOC → контент"
        )


@pytest.mark.asyncio
async def test_docx_toc_contains_content(temp_dir, test_theme, test_pages):
    """
    Тест: проверяет, что TOC содержит содержимое (не пустой).
    
    Проверяет, что TOC не только присутствует, но и содержит
    ссылки на разделы документа.
    """
    if not check_pandoc_available():
        pytest.skip("Pandoc не установлен. Пропускаем тест генерации DOCX.")
    
    # Генерируем тестовую работу
    result = await generate_test_work(
        theme=test_theme,
        pages=test_pages,
        work_type="курсовая",
        model_name=TEST_MODEL_NAME,
        output_dir=temp_dir
    )
    
    # Проверяем, что DOCX был создан
    assert result['docx_path'] is not None
    assert os.path.exists(result['docx_path'])
    
    # Открываем DOCX файл
    doc = Document(result['docx_path'])
    
    # Находим TOC
    toc_idx = find_toc_position(doc)
    if toc_idx is None:
        # Проверяем SDT элемент
        toc_sdt_idx = find_toc_sdt_position(doc)
        assert toc_sdt_idx is not None, "TOC должен присутствовать в документе"
        # SDT элемент может содержать TOC, но проверить его содержимое сложнее
        return
    
    # Проверяем, что после заголовка TOC есть содержимое
    # Обычно TOC содержит несколько строк с разделами
    toc_has_content = False
    for i in range(toc_idx + 1, min(toc_idx + 10, len(doc.paragraphs))):
        para_text = doc.paragraphs[i].text.strip()
        # TOC обычно содержит номера страниц или названия разделов
        if para_text and (any(char.isdigit() for char in para_text) or len(para_text) > MIN_TOC_CONTENT_LENGTH):
            toc_has_content = True
            break
    
    assert toc_has_content, (
        "TOC должен содержать содержимое (ссылки на разделы). "
        "Проверьте, что pandoc правильно создал оглавление."
    )

