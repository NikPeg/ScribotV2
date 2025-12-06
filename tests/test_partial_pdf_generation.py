"""
Тесты для проверки генерации частичной версии работы с QR-кодами.
Проверяет, что количество страниц в частичной версии совпадает с полной версией.
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

from core.document_converter import (  # noqa: E402
    compile_latex_to_pdf,
    create_partial_pdf_with_qr,
)
from gpt.assistant import TEST_MODEL_NAME  # noqa: E402
from scripts.generate import generate_test_work  # noqa: E402


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


class TestPartialPDFGeneration(unittest.TestCase):
    """Тесты для проверки генерации частичной версии PDF с QR-кодами"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_theme = "Тестовая работа для проверки частичной версии"
        self.test_pages = 20
        self.test_user_id = 999999
    
    def tearDown(self):
        """Очистка после каждого теста"""
        import shutil
        if os.path.exists(self.temp_dir):
            with contextlib.suppress(Exception):
                shutil.rmtree(self.temp_dir)
    
    def test_partial_pdf_same_page_count(self):
        """
        Тест: проверяет, что частичная версия PDF (бесплатная) имеет такое же
        количество страниц, как и полная версия (платная).
        
        Частичная версия должна содержать:
        - Первую половину страниц из полной версии
        - Страницы с QR-кодами вместо второй половины
        
        Общее количество страниц должно совпадать.
        """
        if not check_latex_available():
            self.skipTest("LaTeX (pdflatex) не установлен. Пропускаем тест генерации PDF.")
        
        async def run_test():
            # Генерируем полную версию работы
            result = await generate_test_work(
                theme=self.test_theme,
                pages=self.test_pages,
                work_type="курсовая",
                model_name=TEST_MODEL_NAME,
                output_dir=self.temp_dir
            )
            
            # Проверяем, что полная версия была создана
            if result['pdf_path'] is None:
                raise AssertionError(
                    "PDF файл не был создан. Возможно, LaTeX не установлен или произошла ошибка компиляции."
                )
            assert os.path.exists(result['pdf_path']), f"PDF файл должен существовать: {result['pdf_path']}"
            
            # Получаем количество страниц в полной версии
            full_pdf_page_count = get_pdf_page_count(result['pdf_path'])
            assert full_pdf_page_count > 0, "Полная версия PDF должна содержать хотя бы одну страницу"
            
            # Создаем частичную версию с QR-кодами
            # Используем тестовую ссылку на оплату
            test_payment_url = "https://t.me/test_payment"
            
            success, partial_pdf_path = await create_partial_pdf_with_qr(
                full_pdf_path=result['pdf_path'],
                payment_url=test_payment_url,
                user_id=self.test_user_id,
                temp_dir=self.temp_dir,
                output_filename="test_partial"
            )
            
            # Проверяем, что частичная версия была создана успешно
            assert success, f"Не удалось создать частичную версию PDF: {partial_pdf_path}"
            assert os.path.exists(partial_pdf_path), f"Частичная версия PDF должна существовать: {partial_pdf_path}"
            
            # Получаем количество страниц в частичной версии
            partial_pdf_page_count = get_pdf_page_count(partial_pdf_path)
            
            # Проверяем, что количество страниц совпадает
            assert partial_pdf_page_count == full_pdf_page_count, (
                f"Количество страниц должно совпадать! "
                f"Полная версия: {full_pdf_page_count} страниц, "
                f"Частичная версия: {partial_pdf_page_count} страниц"
            )
            
            return full_pdf_page_count, partial_pdf_page_count
        
        # Запускаем асинхронный тест
        full_count, partial_count = asyncio.run(run_test())
        assert full_count == partial_count, (
            f"Количество страниц должно совпадать: полная={full_count}, частичная={partial_count}"
        )
    
    def test_partial_pdf_generation_executes(self):
        """
        Тест: проверяет, что генерация частичной версии выполняется без ошибок.
        Проверяет, что все этапы генерации проходят успешно.
        """
        if not check_latex_available():
            self.skipTest("LaTeX (pdflatex) не установлен. Пропускаем тест генерации PDF.")
        
        async def run_test():
            # Генерируем полную версию работы
            result = await generate_test_work(
                theme=self.test_theme,
                pages=self.test_pages,
                work_type="курсовая",
                model_name=TEST_MODEL_NAME,
                output_dir=self.temp_dir
            )
            
            # Проверяем, что полная версия была создана
            assert result['pdf_path'] is not None, "Полная версия PDF должна быть создана"
            assert os.path.exists(result['pdf_path']), "Полная версия PDF должна существовать"
            
            # Создаем частичную версию
            test_payment_url = "https://t.me/test_payment"
            
            success, partial_pdf_path = await create_partial_pdf_with_qr(
                full_pdf_path=result['pdf_path'],
                payment_url=test_payment_url,
                user_id=self.test_user_id,
                temp_dir=self.temp_dir,
                output_filename="test_partial"
            )
            
            # Проверяем успешность выполнения
            assert success, f"Генерация частичной версии должна быть успешной, но получили ошибку: {partial_pdf_path}"
            assert os.path.exists(partial_pdf_path), "Частичная версия PDF должна быть создана"
            
            # Проверяем, что файл не пустой
            file_size = os.path.getsize(partial_pdf_path)
            assert file_size > 0, "Частичная версия PDF не должна быть пустой"
            
            return True
        
        # Запускаем асинхронный тест
        result = asyncio.run(run_test())
        assert result, "Генерация частичной версии должна выполниться успешно"


if __name__ == '__main__':
    unittest.main()

