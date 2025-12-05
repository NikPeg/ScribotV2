from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core import settings
from core.settings import get_required_channels

def get_main_menu_keyboard():
    """Возвращает клавиатуру для главного меню."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📝 Сгенерировать работу", callback_data="generate_work"
    )
    builder.button(
        text="❓Узнать о Scribo", callback_data="info"
    )
    builder.button(
        text="🤗Чат юзеров", url=settings.chat_url
    )
    builder.button(
        text="📚Отзывы о боте", url=settings.feedback_url
    )
    builder.button(
        text="🆘Поддержка", url=settings.sos_url
    )
    # Расположение: 1, 2, 2
    builder.adjust(1, 2, 2)
    return builder.as_markup()

def get_back_to_menu_keyboard():
    """Возвращает клавиатуру с одной кнопкой "Назад в меню"."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🏠 Главное меню", callback_data="main_menu"
    )
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
        InlineKeyboardButton(text="ChatGPT-3.5", callback_data="model:openai/gpt-3.5-turbo"),
        InlineKeyboardButton(text="DeepSeek (x1.5 цена)", callback_data="model:deepseek/deepseek-chat-v3-0324"),
        InlineKeyboardButton(text="ChatGPT-4 (x2 цена)", callback_data="model:openai/gpt-4o-mini"),
        InlineKeyboardButton(text="🧪 ТЕСТ", callback_data="model:TEST"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_type"),
    ]

    builder.add(*buttons)
    # Каждая кнопка на новой строке
    builder.adjust(1)

    return builder.as_markup()


def get_subscription_keyboard():
    """
    Создает клавиатуру с кнопками для подписки на каналы.
    """
    builder = InlineKeyboardBuilder()
    channels = get_required_channels()
    
    if not channels:
        # Если каналов нет, возвращаем пустую клавиатуру
        return builder.as_markup()
    
    # Добавляем кнопки со ссылками на каналы
    for channel in channels:
        if channel.startswith("@"):
            channel_name = channel[1:]
            builder.button(
                text=f"📢 {channel_name}",
                url=f"https://t.me/{channel_name}"
            )
        else:
            # Если канал задан как ID (отрицательное число для супергрупп),
            # используем формат t.me/c/{channel_id_without_minus}
            # Для обычных каналов с username без @ - просто username
            try:
                # Пытаемся определить, это числовой ID или username
                channel_id = int(channel)
                if channel_id < 0:
                    # Супергруппа - используем формат t.me/c/{id_without_minus}
                    builder.button(
                        text=f"📢 Канал",
                        url=f"https://t.me/c/{abs(channel_id)}"
                    )
                else:
                    # Положительный ID - это может быть публичный канал
                    builder.button(
                        text=f"📢 Канал",
                        url=f"https://t.me/c/{channel_id}"
                    )
            except ValueError:
                # Это username без @
                builder.button(
                    text=f"📢 {channel}",
                    url=f"https://t.me/{channel}"
                )
    
    # Добавляем кнопку "Я подписался"
    builder.button(
        text="✅ Я подписался",
        callback_data="check_subscription"
    )
    
    # Каждая кнопка на новой строке
    builder.adjust(1)
    
    return builder.as_markup()
