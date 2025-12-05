"""
LaTeX шаблон и утилиты для работы с LaTeX документами.
"""

import re
from string import Template

# Шаблон LaTeX документа
# Используем $ вместо {} для подстановки, чтобы избежать конфликтов с LaTeX командами
LATEX_TEMPLATE = r"""
\documentclass[12pt,a4paper,draft]{article}
\usepackage[utf8]{inputenc}
\usepackage[T2A]{fontenc}
\usepackage[russian]{babel}
\usepackage{geometry}
\usepackage{setspace}
\usepackage{indentfirst}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage[hidelinks]{hyperref}

\geometry{left=3cm,right=1.5cm,top=2cm,bottom=2cm}
\onehalfspacing
\setlength{\parindent}{1.25cm}
% Улучшение переноса строк для предотвращения overfull hbox
\emergencystretch=3em
\tolerance=1000
\hfuzz=0.5pt
\sloppy

\begin{document}

% Титульный лист: используем один блок \begin{center}...\end{center}
% вместо окружения \begin{titlepage}...\end{titlepage}, чтобы избежать
% появления пустой страницы между титульным листом и содержанием.
% Окружение titlepage автоматически создает новую страницу после себя,
% что приводит к появлению лишней пустой страницы.
\begin{center}
\vspace*{2cm}
{\Large\textbf{МИНИСТЕРСТВО ОБРАЗОВАНИЯ И НАУКИ РФ}}\\[0.5cm]
{\large Федеральное государственное бюджетное\\
образовательное учреждение высшего образования}\\[0.5cm]
{\Large\textbf{РОССИЙСКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ}}\\[2cm]

{\large Факультет информационных технологий}\\[0.5cm]
{\large Кафедра программной инженерии}\\[3cm]

{\Large\textbf{КУРСОВАЯ РАБОТА}}\\[0.5cm]
{\large по дисциплине}\\[0.3cm]
{\large Информационные технологии}\\[1cm]

{\Large\textbf{Тема: $theme}}\\[3cm]

\begin{flushright}
Выполнил: студент группы ИТ-21\\
Иванов И.И.\\[1cm]
Проверил: к.т.н., доцент\\
Петров П.П.
\end{flushright}

\vspace*{\fill}

Москва \the\year{}

\end{center}

\newpage
$tableofcontents
$content

\end{document}
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
            try:
                # Проверяем, что группа существует
                if match.lastindex and match.lastindex >= 1:
                    bibliography_section = match.group(1)
                    # Умное экранирование: экранируем только неэкранированные &
                    fixed_bibliography = smart_escape_ampersands(bibliography_section)
                    # Заменяем в исходном тексте
                    content = content.replace(bibliography_section, fixed_bibliography)
                    break
            except (IndexError, AttributeError):
                pass
    
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
        try:
            # Проверяем, что группа существует
            if match.lastindex and match.lastindex >= 1:
                content = match.group(1)
            else:
                # Если группы нет, возвращаем как есть
                return match.group(0)
        except (IndexError, AttributeError):
            return match.group(0)
        
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

def create_latex_document(theme: str, content: str, include_toc: bool = True) -> str:
    """
    Создает полный LaTeX документ из шаблона и содержания.
    
    Args:
        theme: Тема работы
        content: Содержание работы (без преамбулы)
        include_toc: Включать ли оглавление (по умолчанию True)
    
    Returns:
        Полный LaTeX документ
    """
    # Очищаем и валидируем контент
    content = clean_latex_content(content)
    
    # Исправляем символы & в списке литературы
    content = fix_bibliography_ampersands(content)
    
    # Формируем оглавление в зависимости от параметра
    if include_toc:
        tableofcontents = "\\tableofcontents\n\n\\newpage"
    else:
        tableofcontents = ""
    
    # Используем Template для безопасной подстановки, чтобы избежать конфликтов
    # с фигурными скобками в LaTeX командах
    template = Template(LATEX_TEMPLATE)
    return template.substitute(theme=theme, content=content, tableofcontents=tableofcontents)


def improve_hyphenation(content: str) -> str:
    """
    Улучшает перенос слов в LaTeX для предотвращения overfull hbox.
    
    Заменяет / на \slash для улучшения переноса в местах типа "слово/слово".
    Добавляет точки переноса для очень длинных слов.
    
    Args:
        content: Исходный LaTeX контент
    
    Returns:
        Контент с улучшенными переносами
    """
    # Применяем улучшения переноса только к обычному тексту
    # Не трогаем LaTeX команды, URL и уже обработанные места
    lines = content.split('\n')
    improved_lines = []
    
    for line in lines:
        # Пропускаем строки с LaTeX командами
        if line.strip().startswith('\\') and any(cmd in line for cmd in ['section', 'subsection', 'begin', 'end', 'item', 'textbf', 'textit', 'slash']):
            improved_lines.append(line)
            continue
        
        # Пропускаем строки с URL
        if 'http' in line.lower() or 'www' in line.lower():
            improved_lines.append(line)
            continue
        
        # Улучшаем переносы в обычном тексте
        improved_line = line
        
        # Заменяем / на \slash\hspace{0pt} в контексте "слово/слово" или "слово / слово"
        # Используем более точный паттерн: буквенно-цифровые последовательности вокруг /
        improved_line = re.sub(
            r'\b([a-zA-Zа-яА-ЯёЁ]+)\s*/\s*([a-zA-Zа-яА-ЯёЁ]+)\b',
            r'\1\\slash\\hspace{0pt}\2',
            improved_line
        )
        
        # Добавляем \hspace{0pt} после пробелов перед длинными словами
        # Это позволяет TeX переносить строку перед длинным словом, если оно не помещается
        def add_break_before_long_word(match):
            space = match.group(1)
            word = match.group(2)
            # Добавляем точку переноса только перед очень длинными словами (более 10 символов)
            if len(word) > 10 and '\\' not in word:
                return space + '\\hspace{0pt}' + word
            return match.group(0)
        
        # Ищем пробелы перед длинными словами
        improved_line = re.sub(
            r'(\s+)([a-zA-Zа-яА-ЯёЁ]{11,})\b',
            add_break_before_long_word,
            improved_line
        )
        
        improved_lines.append(improved_line)
    
    return '\n'.join(improved_lines)


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
    
    # 0. Улучшаем переносы для предотвращения overfull hbox
    content = improve_hyphenation(content)
    
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