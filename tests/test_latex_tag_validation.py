"""
Тесты для функции validate_latex_tags из модуля core.latex_template
"""

import importlib.util
import os
import sys

# Добавляем путь к проекту
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Импортируем модуль
latex_template_path = os.path.join(project_root, 'core', 'latex_template.py')
spec = importlib.util.spec_from_file_location("latex_template", latex_template_path)
latex_template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(latex_template)
validate_latex_tags = latex_template.validate_latex_tags


def test_validate_latex_tags_valid_figure():
    """Тест: валидная фигура с открывающим и закрывающим тегами"""
    content = r"""
\section{Глава 1}
Текст главы.

\begin{figure}
\centering
\includegraphics{image.png}
\caption{Подпись}
\end{figure}

Еще текст.
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Ожидалась валидная фигура, но получена ошибка: {error_msg}"
    assert error_msg == ""


def test_validate_latex_tags_unclosed_figure():
    """Тест: незакрытая фигура"""
    content = r"""
\section{Глава 1}
Текст главы.

\begin{figure}
\centering
\includegraphics{image.png}
\caption{Подпись}

Еще текст.
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert not is_valid, "Ожидалась ошибка для незакрытой фигуры"
    assert "незакрытые теги" in error_msg.lower() or "незакрыт" in error_msg.lower()
    assert "figure" in error_msg.lower()


def test_validate_latex_tags_nested_figures():
    """Тест: вложенные фигуры (не должно быть, но проверяем порядок закрытия)"""
    content = r"""
\section{Глава 1}
\begin{figure}
\begin{figure}
\caption{Вложенная}
\end{figure}
\caption{Внешняя}
\end{figure}
"""
    is_valid, error_msg = validate_latex_tags(content)
    # Вложенные фигуры технически валидны с точки зрения парности тегов
    assert is_valid, f"Вложенные фигуры должны быть валидны, но получена ошибка: {error_msg}"


def test_validate_latex_tags_multiple_figures():
    """Тест: несколько фигур"""
    content = r"""
\section{Глава 1}
\begin{figure}
\caption{Первая}
\end{figure}

\begin{figure}
\caption{Вторая}
\end{figure}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Ожидались валидные фигуры, но получена ошибка: {error_msg}"


def test_validate_latex_tags_wrong_closing_tag():
    """Тест: неправильный закрывающий тег"""
    content = r"""
\section{Глава 1}
\begin{figure}
\caption{Фигура}
\end{table}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert not is_valid, "Ожидалась ошибка для неправильного закрывающего тега"
    assert "несоответствие" in error_msg.lower() or "ожидался" in error_msg.lower()


def test_validate_latex_tags_table():
    """Тест: валидная таблица"""
    content = r"""
\section{Глава 1}
\begin{table}
\caption{Таблица}
\end{table}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Ожидалась валидная таблица, но получена ошибка: {error_msg}"


def test_validate_latex_tags_equation():
    """Тест: валидное уравнение"""
    content = r"""
\section{Глава 1}
\begin{equation}
E = mc^2
\end{equation}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Ожидалось валидное уравнение, но получена ошибка: {error_msg}"


def test_validate_latex_tags_multiple_different_tags():
    """Тест: несколько разных тегов"""
    content = r"""
\section{Глава 1}
\begin{figure}
\caption{Фигура}
\end{figure}

\begin{table}
\caption{Таблица}
\end{table}

\begin{equation}
x = 1
\end{equation}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Ожидались валидные теги, но получена ошибка: {error_msg}"


def test_validate_latex_tags_closing_without_opening():
    """Тест: закрывающий тег без открывающего"""
    content = r"""
\section{Глава 1}
Текст.

\end{figure}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert not is_valid, "Ожидалась ошибка для закрывающего тега без открывающего"
    assert "без соответствующего открывающего" in error_msg.lower() or "без открывающего" in error_msg.lower()


def test_validate_latex_tags_empty_content():
    """Тест: пустой контент"""
    content = ""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Пустой контент должен быть валиден, но получена ошибка: {error_msg}"


def test_validate_latex_tags_no_tags():
    """Тест: контент без тегов"""
    content = r"""
\section{Глава 1}
Обычный текст без тегов.
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Контент без тегов должен быть валиден, но получена ошибка: {error_msg}"


def test_validate_latex_tags_itemize():
    """Тест: валидный список itemize"""
    content = r"""
\section{Глава 1}
\begin{itemize}
\item Первый пункт
\item Второй пункт
\end{itemize}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Ожидался валидный список, но получена ошибка: {error_msg}"


def test_validate_latex_tags_enumerate():
    """Тест: валидный список enumerate"""
    content = r"""
\section{Глава 1}
\begin{enumerate}
\item Первый пункт
\item Второй пункт
\end{enumerate}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Ожидался валидный список, но получена ошибка: {error_msg}"


def test_validate_latex_tags_complex_nested():
    """Тест: сложная структура с несколькими тегами"""
    content = r"""
\section{Глава 1}
Текст.

\begin{figure}
\caption{Фигура 1}
\end{figure}

\begin{itemize}
\item Пункт 1
\item Пункт 2
\end{itemize}

\begin{table}
\caption{Таблица}
\end{table}
"""
    is_valid, error_msg = validate_latex_tags(content)
    assert is_valid, f"Ожидалась валидная сложная структура, но получена ошибка: {error_msg}"

