"""
Тесты для функции smart_escape_dollars из модуля core.latex_template
"""
import importlib.util
import os
import sys

# Добавляем корневую директорию проекта в путь
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Импортируем напрямую из файла, минуя __init__.py чтобы избежать загрузки settings
latex_template_path = os.path.join(project_root, 'core', 'latex_template.py')
spec = importlib.util.spec_from_file_location("latex_template", latex_template_path)
latex_template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(latex_template)
smart_escape_dollars = latex_template.smart_escape_dollars


def test_inline_math_formula():
    """Тест: inline math формулы не должны экранироваться"""
    text = "$C(t)$ -- концентрация в крови"
    result = smart_escape_dollars(text)
    assert result == "$C(t)$ -- концентрация в крови"


def test_multiple_inline_math_formulas():
    """Тест: несколько inline math формул не должны экранироваться"""
    text = "$C_0$ -- начальная доза, $k$ -- константа"
    result = smart_escape_dollars(text)
    assert result == "$C_0$ -- начальная доза, $k$ -- константа"


def test_math_with_superscript():
    """Тест: математические формулы со степенями не должны экранироваться"""
    text = "мин$^{-1}$ для взрослых"
    result = smart_escape_dollars(text)
    assert result == "мин$^{-1}$ для взрослых"


def test_user_example():
    """Тест: пример пользователя с несколькими формулами"""
    text = (
        "где $C(t)$ -- концентрация в крови, $C_0$ -- начальная доза,\n\n"
        "$k$ -- константа элиминации (0.016--0.023 мин$^{-1}$ для взрослых)."
    )
    result = smart_escape_dollars(text)
    expected = (
        "где $C(t)$ -- концентрация в крови, $C_0$ -- начальная доза,\n\n"
        "$k$ -- константа элиминации (0.016--0.023 мин$^{-1}$ для взрослых)."
    )
    assert result == expected


def test_money_dollar_sign():
    """Тест: символы $, обозначающие деньги, должны экранироваться"""
    text = "Стоимость $100"
    result = smart_escape_dollars(text)
    assert result == "Стоимость \\$100"


def test_money_with_text():
    """Тест: деньги в тексте должны экранироваться"""
    text = "Цена составляет $50 за единицу"
    result = smart_escape_dollars(text)
    assert result == "Цена составляет \\$50 за единицу"


def test_mixed_math_and_money():
    """Тест: смесь математических формул и денег"""
    text = "Формула $x = 5$ и цена $10"
    result = smart_escape_dollars(text)
    assert result == "Формула $x = 5$ и цена \\$10"


def test_display_math():
    """Тест: display math формулы ($$...$$) не должны экранироваться"""
    text = "Формула: $$\\int_0^1 x dx = \\frac{1}{2}$$"
    result = smart_escape_dollars(text)
    assert result == "Формула: $$\\int_0^1 x dx = \\frac{1}{2}$$"


def test_alternative_math_syntax():
    r"""Тест: альтернативные синтаксисы \(...\) и \[...\] не должны экранироваться"""
    text = r"Inline: \(x + y\) и display: \[a = b\]"
    result = smart_escape_dollars(text)
    assert result == r"Inline: \(x + y\) и display: \[a = b\]"


def test_already_escaped_dollar():
    """Тест: уже экранированные $ не должны экранироваться повторно"""
    text = "Цена \\$100"
    result = smart_escape_dollars(text)
    assert result == "Цена \\$100"


def test_complex_math_expression():
    """Тест: сложные математические выражения"""
    text = "$C(t) = C_0 e^{-kt}$ где $k = 0.016$"
    result = smart_escape_dollars(text)
    assert result == "$C(t) = C_0 e^{-kt}$ где $k = 0.016$"


def test_multiple_dollar_signs_money():
    """Тест: несколько символов $ подряд (не формула) должны экранироваться"""
    text = "Цены: $10, $20, $30"
    result = smart_escape_dollars(text)
    assert result == "Цены: \\$10, \\$20, \\$30"


def test_empty_string():
    """Тест: пустая строка"""
    text = ""
    result = smart_escape_dollars(text)
    assert result == ""


def test_no_dollars():
    """Тест: текст без символов $"""
    text = "Обычный текст без долларов"
    result = smart_escape_dollars(text)
    assert result == "Обычный текст без долларов"


def test_single_dollar_sign():
    """Тест: одиночный символ $ должен экранироваться"""
    text = "Цена $"
    result = smart_escape_dollars(text)
    assert result == "Цена \\$"


def test_math_with_spaces():
    """Тест: математические формулы с пробелами"""
    text = "$x + y = z$ и $a = b$"
    result = smart_escape_dollars(text)
    assert result == "$x + y = z$ и $a = b$"


def test_nested_math_expressions():
    """Тест: вложенные математические выражения"""
    text = "Формула $f(x) = x^2$ и её производная $f'(x) = 2x$"
    result = smart_escape_dollars(text)
    assert result == "Формула $f(x) = x^2$ и её производная $f'(x) = 2x$"
