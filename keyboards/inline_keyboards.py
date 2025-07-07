from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Этот файл содержит функции для создания и возврата всех inline-клавиатур бота.

def get_main_menu_keyboard():
    """Возвращает клавиатуру для главного меню."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📝 Сгенерировать работу", callback_data="generate_work"
    )
    # Здесь можно будет добавить другие кнопки, например "О боте", "Поддержка"
    builder.adjust(1)
    return builder.as_markup()

def get_pages_keyboard():
    """Возвращает клавиатуру для выбора количества страниц."""
    builder = InlineKeyboardBuilder()

    # Кнопки согласно ТЗ
    buttons = [
        InlineKeyboardButton(text="🤷‍♂️ Любой", callback_data="pages:20"),
        InlineKeyboardButton(text="1-2", callback_data="pages:2"),
        InlineKeyboardButton(text="5-10", callback_data="pages:10"),
        InlineKeyboardButton(text="10-20", callback_data="pages:20"),
        InlineKeyboardButton(text="20-30", callback_data="pages:30"),
        InlineKeyboardButton(text="30-40", callback_data="pages:40"),
        InlineKeyboardButton(text="40-50", callback_data="pages:50"),
        InlineKeyboardButton(text="50-60", callback_data="pages:60"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    ]

    builder.add(*buttons)
    # Расположение кнопок: 2 в первой строке, по 3 в следующих двух, 1 в последней
    builder.adjust(2, 3, 3, 1)

    return builder.as_markup()

def get_work_type_keyboard():
    """Возвращает клавиатуру для выбора типа работы."""
    builder = InlineKeyboardBuilder()

    buttons = [
        InlineKeyboardButton(text="Курсовая", callback_data="type:coursework"),
        InlineKeyboardButton(text="Дипломная", callback_data="type:diploma"),
        InlineKeyboardButton(text="Реферат", callback_data="type:reference"),
        InlineKeyboardButton(text="Доклад", callback_data="type:report"),
        InlineKeyboardButton(text="Исследование", callback_data="type:research"),
        InlineKeyboardButton(text="Отчет по практике", callback_data="type:practice"),
        InlineKeyboardButton(text="🤷‍♂️ Любая", callback_data="type:reference"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_pages"),
    ]

    builder.add(*buttons)
    # Расположение кнопок: по 3 в первых двух строках, 1 в третьей, 1 в последней
    builder.adjust(3, 3, 1, 1)

    return builder.as_markup()

def get_model_keyboard():
    """Возвращает клавиатуру для выбора модели GPT."""
    builder = InlineKeyboardBuilder()

    buttons = [
        InlineKeyboardButton(text="GPT-3.5 Turbo", callback_data="model:gpt-3.5-turbo"),
        InlineKeyboardButton(text="GPT-4o mini (x2 цена)", callback_data="model:gpt-4o-mini"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_type"),
    ]

    builder.add(*buttons)
    # Каждая кнопка на новой строке
    builder.adjust(1)

    return builder.as_markup()
