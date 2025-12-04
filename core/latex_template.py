"""
LaTeX шаблон и утилиты для работы с LaTeX документами.
"""

import re

# Шаблон LaTeX документа
LATEX_TEMPLATE = r"""
\documentclass[12pt,a4paper,draft]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T2A]{{fontenc}}
\usepackage[russian]{{babel}}
\usepackage{{geometry}}
\usepackage{{setspace}}
\usepackage{{indentfirst}}
\usepackage{{amsmath}}
\usepackage{{amsfonts}}
\usepackage{{amssymb}}
\usepackage{{graphicx}}
\usepackage[hidelinks]{{hyperref}}

\geometry{{left=3cm,right=1.5cm,top=2cm,bottom=2cm}}
\onehalfspacing
\setlength{{\parindent}}{{1.25cm}}

\begin{{document}}

\begin{{titlepage}}
\centering
\vspace*{{2cm}}
{{\Large\textbf{{МИНИСТЕРСТВО ОБРАЗОВАНИЯ И НАУКИ РФ}}}}\\[0.5cm]
{{\large Федеральное государственное бюджетное\\
образовательное учреждение высшего образования}}\\[0.5cm]
{{\Large\textbf{{РОССИЙСКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ}}}}\\[2cm]

{{\large Факультет информационных технологий}}\\[0.5cm]
{{\large Кафедра программной инженерии}}\\[3cm]

{{\Large\textbf{{КУРСОВАЯ РАБОТА}}}}\\[0.5cm]
{{\large по дисциплине}}\\[0.3cm]
{{\large Информационные технологии}}\\[1cm]

{{\Large\textbf{{Тема: {theme}}}}}\\[3cm]

\begin{{flushright}}
Выполнил: студент группы ИТ-21\\
Иванов И.И.\\[1cm]
Проверил: к.т.н., доцент\\
Петров П.П.
\end{{flushright}}

\vfill
{{\large Москва 2025}}
\end{{titlepage}}

\tableofcontents
\newpage

{content}

\end{{document}}
"""

def fix_bibliography_ampersands(content: str) -> str:
    """
    Экранирует символы & только в разделе "Список использованных источников".
    Учитывает случаи, когда GPT уже экранировал символы.
    """
    # Ищем раздел со списком литературы
    bibliography_patterns = [
        r'(\\section\{[^}]*(?:Список|список)[^}]*(?:литературы|источников|использованных)[^}]*\}.*?)(?=\\section|\Z)',
        r'(\\section\*\{[^}]*(?:Список|список)[^}]*(?:литературы|источников|использованных)[^}]*\}.*?)(?=\\section|\Z)',
        r'(\\chapter\{[^}]*(?:Список|список)[^}]*(?:литературы|источников|использованных)[^}]*\}.*?)(?=\\chapter|\Z)'
    ]
    
    for pattern in bibliography_patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            bibliography_section = match.group(1)
            # Умное экранирование: экранируем только неэкранированные &
            fixed_bibliography = smart_escape_ampersands(bibliography_section)
            # Заменяем в исходном тексте
            content = content.replace(bibliography_section, fixed_bibliography)
            break
    
    return content


def smart_escape_ampersands(text: str) -> str:
    """
    Умно экранирует символы &, избегая двойного экранирования.
    
    Args:
        text: Текст для обработки
    
    Returns:
        Текст с правильно экранированными символами &
    """
    # Сначала нормализуем - убираем двойное экранирование если оно есть
    text = text.replace('\\\\&', '\\&')
    
    # Теперь экранируем только неэкранированные &
    # Используем negative lookbehind чтобы не трогать уже экранированные
    text = re.sub(r'(?<!\\)&', r'\\&', text)
    
    return text


def smart_escape_dollars(text: str) -> str:
    r"""
    Умно экранирует символы $, пропуская те, что используются в математических формулах.
    
    Экранирует только те $, которые обозначают деньги, а не математические формулы.
    Поддерживает синтаксисы: $...$, $$...$$, \(...\), \[...\]
    
    Args:
        text: Текст для обработки
    
    Returns:
        Текст с правильно экранированными символами $ (только не-математические)
    """
    # Временные маркеры для замены математических формул
    markers = []
    marker_counter = 0
    
    def replace_math_with_marker(match):
        nonlocal marker_counter
        marker = f"__MATH_MARKER_{marker_counter}__"
        markers.append((marker, match.group(0)))
        marker_counter += 1
        return marker
    
    # Обрабатываем математические формулы в правильном порядке
    # 1. Сначала display math $$...$$ (чтобы не перехватить часть inline math)
    text = re.sub(r'\$\$.*?\$\$', replace_math_with_marker, text, flags=re.DOTALL)
    
    # 2. Альтернативные синтаксисы \(...\) и \[...\]
    text = re.sub(r'\\\(.*?\\\)', replace_math_with_marker, text, flags=re.DOTALL)
    text = re.sub(r'\\\[.*?\\\]', replace_math_with_marker, text, flags=re.DOTALL)
    
    # 3. Inline math $...$ (обрабатываем после $$, чтобы не перехватить часть display math)
    # Используем нежадное сопоставление для поиска пар $
    # Паттерн ищет $, за которым следует любой текст (не содержащий $), и затем закрывающий $
    # Но проверяем, что содержимое выглядит как математическое выражение (не просто число)
    def replace_inline_math_if_valid(match):
        content = match.group(1)
        # Проверяем, что содержимое содержит математические символы:
        # буквы, операторы (+, -, *, /, =, <, >), скобки, индексы (^, _), функции и т.д.
        # Если это просто число или число с единицами измерения - это не формула
        has_math_chars = bool(re.search(r'[a-zA-Z_^{}\(\)\[\]+\-*/=<>]', content))
        # Если содержимое - просто число (возможно с точкой, запятой, пробелами), это не формула
        is_just_number = bool(re.match(r'^[\d\s.,]+$', content.strip()))
        
        if has_math_chars and not is_just_number:
            return replace_math_with_marker(match)
        else:
            # Это не формула, возвращаем как есть (будет экранировано позже)
            return match.group(0)
    
    text = re.sub(r'(?<!\$)\$(?!\$)((?:(?!\$).)*?)\$(?!\$)', replace_inline_math_if_valid, text, flags=re.DOTALL)
    
    # Теперь экранируем все оставшиеся $ (которые не в математических формулах)
    # Сначала убираем двойное экранирование если оно есть
    text = text.replace('\\\\$', '\\$')
    
    # Экранируем только неэкранированные $
    text = re.sub(r'(?<!\\)\$', r'\\$', text)
    
    # Возвращаем математические формулы обратно
    for marker, original_math in markers:
        text = text.replace(marker, original_math)
    
    return text


def remove_markdown_code_blocks(content: str) -> str:
    """
    Удаляет markdown блоки кода (```latex в начале и ``` в конце).
    
    Args:
        content: Исходный контент
    
    Returns:
        Контент без markdown блоков кода
    """
    if not content:
        return content
    
    # Убираем начальный блок ```latex или ```
    # Проверяем начало строки (может быть с пробелами или переносами)
    content = re.sub(r'^[\s\n]*```\s*latex\s*\n?', '', content, flags=re.IGNORECASE | re.MULTILINE)
    content = re.sub(r'^[\s\n]*```\s*\n?', '', content, flags=re.MULTILINE)
    
    # Убираем конечный блок ```
    content = re.sub(r'\n?```\s*[\s\n]*$', '', content, flags=re.MULTILINE)
    
    return content.strip()

def create_latex_document(theme: str, content: str) -> str:
    """
    Создает полный LaTeX документ из шаблона и содержания.
    
    Args:
        theme: Тема работы
        content: Содержание работы (без преамбулы)
    
    Returns:
        Полный LaTeX документ
    """
    # Очищаем и валидируем контент
    content = clean_latex_content(content)
    
    # Исправляем символы & в списке литературы
    content = fix_bibliography_ampersands(content)
    
    # Создаем полный LaTeX документ
    return LATEX_TEMPLATE.format(theme=theme, content=content)


def clean_latex_content(content: str) -> str:
    """
    Очищает LaTeX контент от потенциально проблемных элементов.
    
    Args:
        content: Исходный LaTeX контент
    
    Returns:
        Очищенный LaTeX контент
    """
    # Убираем markdown блоки кода (```latex в начале и ``` в конце)
    content = remove_markdown_code_blocks(content)
    
    # 1. Умное экранирование $ (только не-математические)
    content = smart_escape_dollars(content)
    
    # 2. Экранируем другие специальные символы LaTeX (кроме тех, что в командах)
    problematic_chars = {
        '#': '\\#',
        '%': '\\%',
        '^': '\\textasciicircum{}',
        '_': '\\_',
        '~': '\\textasciitilde{}',
    }
    
    # Применяем замены только вне LaTeX команд
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Пропускаем строки с LaTeX командами
        if line.strip().startswith('\\') and any(cmd in line for cmd in ['section', 'subsection', 'begin', 'end']):
            cleaned_lines.append(line)
            continue
            
        # Очищаем обычные строки текста
        cleaned_line = line
        for char, replacement in problematic_chars.items():
            # Заменяем только если символ не является частью LaTeX команды
            if char in cleaned_line and '\\' not in cleaned_line:
                cleaned_line = cleaned_line.replace(char, replacement)
        
        cleaned_lines.append(cleaned_line)
    
    content = '\n'.join(cleaned_lines)
    
    # 2. Убираем пустые команды и некорректные конструкции
    content = re.sub(r'\\[a-zA-Z]+\{\s*\}', '', content)  # Пустые команды
    content = re.sub(r'\{\s*\}', '', content)  # Пустые скобки
    content = re.sub(r'\\\\+', '\\\\', content)  # Множественные переносы строк
    
    # 3. Исправляем некорректные переносы строк
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # Множественные пустые строки
    
    # 4. Убираем trailing whitespace
    lines = [line.rstrip() for line in content.split('\n')]
    content = '\n'.join(lines)
    
    return content