"""
Тесты для валидации плана работы
"""
import os
import sys
import unittest

# Добавляем корневую директорию проекта в путь
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from core.page_calculator import count_plan_items, validate_work_plan  # noqa: E402


class TestPlanValidation(unittest.TestCase):
    """Тесты для валидации плана работы"""

    def test_count_plan_items_simple(self):
        """Тест: подсчет пунктов в простом плане"""
        chapters = [
            {"title": "Введение", "subsections": []},
            {"title": "Глава 1", "subsections": ["1.1 Подраздел 1", "1.2 Подраздел 2"]},
            {"title": "Заключение", "subsections": []},
        ]
        result = count_plan_items(chapters)
        # 3 главы + 2 подраздела = 5 пунктов
        assert result == 5  # noqa: PLR2004

    def test_count_plan_items_no_subsections(self):
        """Тест: подсчет пунктов без подразделов"""
        chapters = [
            {"title": "Введение", "subsections": []},
            {"title": "Глава 1", "subsections": []},
            {"title": "Глава 2", "subsections": []},
        ]
        result = count_plan_items(chapters)
        # 3 главы = 3 пункта
        assert result == 3  # noqa: PLR2004

    def test_count_plan_items_empty(self):
        """Тест: подсчет пунктов в пустом плане"""
        chapters = []
        result = count_plan_items(chapters)
        assert result == 0

    def test_count_plan_items_many_subsections(self):
        """Тест: подсчет пунктов с большим количеством подразделов"""
        chapters = [
            {"title": "Глава 1", "subsections": ["1.1", "1.2", "1.3", "1.4"]},
            {"title": "Глава 2", "subsections": ["2.1", "2.2"]},
        ]
        result = count_plan_items(chapters)
        # 2 главы + 6 подразделов = 8 пунктов
        assert result == 8  # noqa: PLR2004

    def test_validate_work_plan_valid(self):
        """Тест: валидация валидного плана"""
        plan_text = """1. Введение
2. Глава 1
   2.1 Подраздел 1
   2.2 Подраздел 2
3. Глава 2
   3.1 Подраздел 1
   3.2 Подраздел 2
4. Заключение"""
        # Для 10 страниц минимум = 10 // 3 = 3 пункта
        # В плане: 4 главы + 4 подраздела = 8 пунктов >= 3
        is_valid, items_count = validate_work_plan(plan_text, 10)
        assert is_valid
        assert items_count == 8  # noqa: PLR2004

    def test_validate_work_plan_invalid(self):
        """Тест: валидация невалидного плана (слишком мало пунктов)"""
        plan_text = """1. Введение
2. Глава 1
3. Заключение"""
        # Для 15 страниц минимум = 15 // 3 = 5 пунктов
        # В плане: 3 главы = 3 пункта < 5
        is_valid, items_count = validate_work_plan(plan_text, 15)
        assert not is_valid
        assert items_count == 3  # noqa: PLR2004

    def test_validate_work_plan_minimum_one(self):
        """Тест: минимум всегда 1, даже для малого количества страниц"""
        plan_text = """1. Введение"""
        # Для 2 страниц минимум = max(1, 2 // 3) = max(1, 0) = 1
        is_valid, items_count = validate_work_plan(plan_text, 2)
        assert is_valid  # 1 пункт >= 1
        assert items_count == 1

    def test_validate_work_plan_exact_threshold(self):
        """Тест: валидация плана на границе (ровно минимум)"""
        plan_text = """1. Введение
2. Глава 1
   2.1 Подраздел"""
        # Для 9 страниц минимум = 9 // 3 = 3 пункта
        # В плане: 2 главы + 1 подраздел = 3 пункта = 3
        is_valid, items_count = validate_work_plan(plan_text, 9)
        assert is_valid
        assert items_count == 3  # noqa: PLR2004

    def test_validate_work_plan_invalid_text(self):
        """Тест: валидация некорректного текста плана"""
        plan_text = "Это не план, а просто текст"
        is_valid, items_count = validate_work_plan(plan_text, 10)
        assert not is_valid
        assert items_count == 0

    def test_validate_work_plan_empty(self):
        """Тест: валидация пустого плана"""
        plan_text = ""
        is_valid, items_count = validate_work_plan(plan_text, 10)
        assert not is_valid
        assert items_count == 0

    def test_validate_work_plan_large_work(self):
        """Тест: валидация плана для большой работы"""
        plan_text = """1. Введение
2. Глава 1
   2.1 Подраздел 1
   2.2 Подраздел 2
   2.3 Подраздел 3
3. Глава 2
   3.1 Подраздел 1
   3.2 Подраздел 2
4. Глава 3
   4.1 Подраздел 1
5. Заключение"""
        # Для 30 страниц минимум = 30 // 3 = 10 пунктов
        # В плане: 5 глав + 6 подразделов = 11 пунктов >= 10
        is_valid, items_count = validate_work_plan(plan_text, 30)
        assert is_valid
        assert items_count == 11  # noqa: PLR2004

    def test_validate_work_plan_with_bibliography(self):
        """Тест: валидация плана со списком литературы"""
        plan_text = """1. Введение
2. Глава 1
   2.1 Подраздел 1
   2.2 Подраздел 2
3. Глава 2
   3.1 Подраздел 1
4. Список использованных источников"""
        # Для 12 страниц минимум = 12 // 3 = 4 пункта
        # В плане: 4 главы + 3 подраздела = 7 пунктов >= 4
        is_valid, items_count = validate_work_plan(plan_text, 12)
        assert is_valid
        assert items_count == 7  # noqa: PLR2004


if __name__ == "__main__":
    unittest.main()

