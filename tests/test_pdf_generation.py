"""
Тесты для проверки генерации PDF документов.
Проверяет корректность количества страниц и отсутствие лишних страниц.
"""
import asyncio
import contextlib
import os
import subprocess
import sys
import tempfile
import unittest

# Добавляем корневую директорию проекта в путь
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from gpt.assistant import TEST_MODEL_NAME  # noqa: E402
from scripts.generate import generate_test_work  # noqa: E402

# Константы для тестов
EXPECTED_PDF_PAGES = 426  # Ожидаемое количество страниц в тестовом режиме
MAX_REASONABLE_PAGES = 10000  # Максимальное разумное количество страниц для проверки


def check_latex_available() -> bool:
    """
    Проверяет, доступен ли LaTeX (pdflatex) в системе.
    
    Returns:
        True, если pdflatex доступен, False иначе
    """
    try:
        result = subprocess.run(
            ['pdflatex', '--version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_pdf_page_count(pdf_path: str) -> int:
    """
    Получает количество страниц в PDF файле используя pdfinfo.
    
    Args:
        pdf_path: Путь к PDF файлу
    
    Returns:
        Количество страниц в PDF
    """
    try:
        result = subprocess.run(
            ['pdfinfo', pdf_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        raise ValueError(f"Не удалось получить количество страниц из pdfinfo: {result.stderr}")
    except FileNotFoundError as err:
        raise RuntimeError("pdfinfo не установлен. Установите poppler-utils для проверки PDF.") from err
    except subprocess.TimeoutExpired as err:
        raise RuntimeError("Таймаут при проверке PDF файла") from err


class TestPDFGeneration(unittest.TestCase):
    """Тесты для проверки генерации PDF документов"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_theme = "Тестовая работа для проверки генерации"
        self.test_pages = 427
    
    def tearDown(self):
        """Очистка после каждого теста"""
        import shutil
        if os.path.exists(self.temp_dir):
            with contextlib.suppress(Exception):
                shutil.rmtree(self.temp_dir)
    
    def test_pdf_generation_page_count(self):
        """
        Тест: проверяет, что сгенерированный PDF имеет ожидаемое количество страниц.
        В тестовом режиме генерируется фиксированный контент, поэтому проверяем
        что PDF создается корректно и имеет разумное количество страниц.
        """
        if not check_latex_available():
            self.skipTest("LaTeX (pdflatex) не установлен. Пропускаем тест генерации PDF.")
        
        async def run_test():
            result = await generate_test_work(
                theme=self.test_theme,
                pages=self.test_pages,
                work_type="курсовая",
                model_name=TEST_MODEL_NAME,
                output_dir=self.temp_dir
            )
            
            # Проверяем, что PDF был создан
            if result['pdf_path'] is None:
                raise AssertionError(
                    "PDF файл не был создан. Возможно, LaTeX не установлен или произошла ошибка компиляции. "
                    "Проверьте вывод генерации для деталей."
                )
            assert os.path.exists(result['pdf_path']), f"PDF файл должен существовать: {result['pdf_path']}"
            
            # Получаем количество страниц в PDF
            pdf_page_count = get_pdf_page_count(result['pdf_path'])
            
            # В тестовом режиме генерируется фиксированный контент
            # Проверяем, что PDF имеет разумное количество страниц (не 0, не слишком много)
            assert pdf_page_count > 0, "PDF должен содержать хотя бы одну страницу"
            assert pdf_page_count < MAX_REASONABLE_PAGES, "PDF не должен содержать слишком много страниц"
            
            # Проверяем, что количество страниц соответствует ожидаемому для тестового режима
            # В тестовом режиме должно быть около 426 страниц
            assert pdf_page_count == EXPECTED_PDF_PAGES, (
                f"PDF должен содержать {EXPECTED_PDF_PAGES} страниц, но содержит {pdf_page_count}"
            )
            
            return pdf_page_count
        
        # Запускаем асинхронный тест
        page_count = asyncio.run(run_test())
        assert page_count == EXPECTED_PDF_PAGES, f"PDF должен содержать ровно {EXPECTED_PDF_PAGES} страниц"
    
    def test_no_extra_pages_after_title(self):
        """
        Тест: проверяет, что нет лишних пустых страниц между титульным листом и содержанием.
        Это критичный тест для отлова проблемы с пустыми страницами.
        """
        if not check_latex_available():
            self.skipTest("LaTeX (pdflatex) не установлен. Пропускаем тест генерации PDF.")
        
        async def run_test():
            result = await generate_test_work(
                theme=self.test_theme,
                pages=self.test_pages,
                work_type="курсовая",
                model_name=TEST_MODEL_NAME,
                output_dir=self.temp_dir
            )
            
            # Проверяем, что PDF был создан
            if result['pdf_path'] is None:
                raise AssertionError(
                    "PDF файл не был создан. Возможно, LaTeX не установлен или произошла ошибка компиляции. "
                    "Проверьте вывод генерации для деталей."
                )
            assert os.path.exists(result['pdf_path'])
            
            # Получаем количество страниц в PDF
            pdf_page_count = get_pdf_page_count(result['pdf_path'])
            
            # Проверяем, что количество страниц соответствует ожидаемому
            # Если есть лишняя страница, количество будет отличаться
            assert pdf_page_count == EXPECTED_PDF_PAGES, (
                f"Обнаружена проблема с количеством страниц! "
                f"Ожидалось {EXPECTED_PDF_PAGES}, получено {pdf_page_count}. "
                f"Возможно, есть лишняя пустая страница между титульным листом и содержанием."
            )
            
            return pdf_page_count
        
        page_count = asyncio.run(run_test())
        assert page_count == EXPECTED_PDF_PAGES


if __name__ == '__main__':
    unittest.main()

