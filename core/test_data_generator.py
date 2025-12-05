"""
Модуль для генерации тестовых данных (умный lorem ipsum) в тестовом режиме.
"""

import random

# Константа для тестового режима
TEST_MODEL_NAME = "TEST"


def generate_test_plan(theme: str, pages: int, _work_type: str) -> str:
    """
    Генерирует тестовый план работы, который можно распарсить.
    
    Args:
        theme: Тема работы
        pages: Количество страниц
        work_type: Тип работы
    
    Returns:
        Структурированный план работы
    """
    # Определяем количество глав в зависимости от объема
    if pages <= 10:
        num_chapters = 2
    elif pages <= 20:
        num_chapters = 3
    else:
        num_chapters = 4
    
    plan_lines = [
        "1. Введение",
        "",
        f"2. Теоретические основы исследования темы '{theme}'",
        "   2.1 Основные понятия и определения",
        "   2.2 Исторический контекст развития",
        "   2.3 Современное состояние вопроса",
    ]
    
    # Добавляем дополнительные главы
    chapter_titles = [
        "Практические аспекты применения",
        "Анализ существующих подходов",
        "Методология исследования",
        "Результаты и их интерпретация",
    ]
    
    for i in range(3, num_chapters + 2):
        if i - 3 < len(chapter_titles):
            title = chapter_titles[i - 3]
            plan_lines.append(f"{i}. {title}")
            plan_lines.append(f"   {i}.1 Первый подраздел")
            plan_lines.append(f"   {i}.2 Второй подраздел")
            if pages > 20:
                plan_lines.append(f"   {i}.3 Третий подраздел")
            plan_lines.append("")
    
    plan_lines.append(f"{num_chapters + 2}. Заключение")
    plan_lines.append("")
    plan_lines.append(f"{num_chapters + 3}. Список использованных источников")
    
    return "\n".join(plan_lines)


def generate_test_bibliography(theme: str) -> str:
    """
    Генерирует фейковую библиографию в формате LaTeX.
    
    Args:
        theme: Тема работы
    
    Returns:
        Библиография в формате LaTeX thebibliography
    """
    # Генерируем список фейковых источников
    authors = [
        "Иванов", "Петров", "Сидоров", "Козлов", "Смирнов",
        "Ананьева", "Волкова", "Новикова", "Морозова", "Петрова",
        "Соколов", "Лебедев", "Кузнецов", "Попов", "Васильев"
    ]
    
    first_names = [
        "А.И.", "В.П.", "С.М.", "Д.А.", "Е.В.",
        "Т.И.", "Н.С.", "О.А.", "М.В.", "Л.П.",
        "И.А.", "П.В.", "М.С.", "А.Д.", "В.Е."
    ]
    
    cities = ["М.", "СПб.", "Н. Новгород", "Екатеринбург", "Казань"]
    publishers = ["Наука", "Высшая школа", "Академия", "Университет", "Издательство"]
    years = list(range(2015, 2024))
    
    bibliography_lines = [
        "\\section{Список использованных источников}",
        "",
        "\\begin{thebibliography}{99}"
    ]
    
    # Генерируем 15-20 источников
    num_sources = random.randint(15, 20)
    
    for i in range(1, num_sources + 1):
        author = random.choice(authors)
        first_name = random.choice(first_names)
        city = random.choice(cities)
        publisher = random.choice(publishers)
        year = random.choice(years)
        
        # Разные типы источников
        source_types = [
            f"{author}, {first_name} Исследование темы: {theme} / "
            f"{first_name} {author}. - {city}: {publisher}, {year}. - "
            f"{random.randint(200, 500)} с.",
            
            f"{author}, {first_name} Современные подходы к изучению "
            f"вопросов по теме '{theme}' / {first_name} {author} // "
            f"Вестник университета. - {year}. - № {random.randint(1, 12)}. - "
            f"С. {random.randint(10, 200)}-{random.randint(201, 400)}.",
            
            f"{author}, {first_name} Методология исследования: "
            f"практическое руководство / {first_name} {author}. - "
            f"{city}: {publisher}, {year}. - {random.randint(150, 400)} с.",
        ]
        
        source_text = random.choice(source_types)
        bibliography_lines.append(f"\\bibitem{{source{i}}} {source_text}")
    
    bibliography_lines.append("\\end{thebibliography}")
    
    return "\n".join(bibliography_lines)


def generate_test_content(chapter_title: str, theme: str, target_pages: float) -> str:
    """
    Генерирует тестовое содержание главы в формате LaTeX.
    
    Args:
        chapter_title: Название главы
        theme: Тема работы
        target_pages: Целевое количество страниц
    
    Returns:
        Содержание главы в формате LaTeX
    """
    title_lower = chapter_title.lower()
    
    # Генерируем базовый lorem ipsum текст
    lorem_paragraphs = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
        
        "Duis aute irure dolor in reprehenderit in voluptate velit esse "
        "cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat "
        "cupidatat non proident, sunt in culpa qui officia deserunt mollit.",
        
        "Sed ut perspiciatis unde omnis iste natus error sit voluptatem "
        "accusantium doloremque laudantium, totam rem aperiam, eaque ipsa "
        "quae ab illo inventore veritatis et quasi architecto beatae vitae.",
        
        "At vero eos et accusamus et iusto odio dignissimos ducimus qui "
        "blanditiis praesentium voluptatum deleniti atque corrupti quos dolores "
        "et quas molestias excepturi sint occaecati cupiditate non provident.",
        
        "Similique sunt in culpa qui officia deserunt mollitia animi, id est "
        "laborum et dolorum fuga. Et harum quidem rerum facilis est et expedita "
        "distinctio. Nam libero tempore, cum soluta nobis est eligendi optio.",
        
        "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, "
        "consectetur, adipisci velit, sed quia non numquam eius modi tempora "
        "incidunt ut labore et dolore magnam aliquam quaerat voluptatem.",
        
        "Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis "
        "suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur? "
        "Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse.",
    ]
    
    # Специальная обработка для разных типов глав
    if 'введение' in title_lower:
        content = "\\section{Введение}\n\n"
        intro_text = (
            f"Данная работа посвящена исследованию темы '{theme}'. "
            f"Актуальность исследования обусловлена необходимостью "
            f"изучения современных подходов к данной проблематике. "
            f"Целью работы является анализ существующих методов и "
            f"разработка практических рекомендаций. "
        )
        content += intro_text
        # Генерируем фиксированное количество параграфов (примерно 3-4 параграфа на страницу)
        num_paragraphs = max(3, int(target_pages * 3))
        for _ in range(num_paragraphs):
            para = random.choice(lorem_paragraphs)
            content += f"\n\n{para} "
            # Добавляем случайные ссылки на источники
            if random.random() > 0.5:
                source_num = random.randint(1, 20)
                content += f"\\cite{{source{source_num}}} "
        
    elif 'заключение' in title_lower:
        content = "\\section{Заключение}\n\n"
        conclusion_text = (
            f"В результате проведенного исследования темы '{theme}' "
            f"были получены следующие выводы. Во-первых, было установлено, "
            f"что современные подходы требуют дальнейшего изучения. "
            f"Во-вторых, практическое применение полученных результатов "
            f"может способствовать развитию данной области. "
        )
        content += conclusion_text
        # Генерируем фиксированное количество параграфов
        num_paragraphs = max(3, int(target_pages * 3))
        for _ in range(num_paragraphs):
            para = random.choice(lorem_paragraphs)
            content += f"\n\n{para} "
            if random.random() > 0.5:
                source_num = random.randint(1, 20)
                content += f"\\cite{{source{source_num}}} "
        
    elif 'список' in title_lower or 'библиография' in title_lower:
        # Для библиографии используем специальную функцию
        return generate_test_bibliography(theme)
        
    else:
        # Обычная глава
        content = f"\\section{{{chapter_title}}}\n\n"
        chapter_intro = (
            f"В данной главе рассматриваются вопросы, связанные с темой "
            f"'{theme}'. Особое внимание уделяется теоретическим аспектам "
            f"и практическому применению полученных знаний. "
        )
        content += chapter_intro
        
        # Генерируем фиксированное количество параграфов
        num_paragraphs = max(3, int(target_pages * 3))
        for _ in range(num_paragraphs):
            para = random.choice(lorem_paragraphs)
            content += f"\n\n{para} "
            if random.random() > 0.3:
                source_num = random.randint(1, 20)
                content += f"\\cite{{source{source_num}}} "
    
    return content


def generate_test_subsection(subsection_title: str, _chapter_title: str, theme: str, target_pages: float) -> str:
    """
    Генерирует тестовое содержание подраздела.
    
    Args:
        subsection_title: Название подраздела
        chapter_title: Название главы
        theme: Тема работы
        target_pages: Целевое количество страниц
    
    Returns:
        Содержание подраздела в формате LaTeX
    """
    lorem_paragraphs = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        
        "Duis aute irure dolor in reprehenderit in voluptate velit esse "
        "cillum dolore eu fugiat nulla pariatur.",
        
        "Sed ut perspiciatis unde omnis iste natus error sit voluptatem "
        "accusantium doloremque laudantium.",
    ]
    
    content = f"\\subsection{{{subsection_title}}}\n\n"
    intro = (
        f"В данном подразделе рассматриваются аспекты '{subsection_title}' "
        f"в контексте темы '{theme}'. "
    )
    content += intro
    
    # Генерируем фиксированное количество параграфов (для подраздела меньше)
    num_paragraphs = max(2, int(target_pages * 4))
    for _ in range(num_paragraphs):
        para = random.choice(lorem_paragraphs)
        content += f"\n\n{para} "
        if random.random() > 0.4:
            source_num = random.randint(1, 20)
            content += f"\\cite{{source{source_num}}} "
    
    return content


def generate_test_subsections_list(_chapter_title: str, _theme: str) -> str:
    """
    Генерирует список подразделов для главы (если они не были указаны в плане).
    
    Args:
        chapter_title: Название главы
        theme: Тема работы
    
    Returns:
        Текст со списком подразделов (каждый с новой строки)
    """
    subsections = [
        "Основные понятия и определения",
        "Теоретические основы",
        "Практические аспекты",
        "Анализ результатов",
    ]
    
    # Возвращаем 2-3 случайных подраздела
    selected = random.sample(subsections, k=random.randint(2, 3))
    return "\n".join(selected)

