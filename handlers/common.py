import random

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core import OrderStates, settings
from db.database import get_or_create_user
from keyboards import get_back_to_menu_keyboard, get_main_menu_keyboard
from utils.admin_logger import send_admin_log

common_router = Router()


def get_start_message() -> str:
    """
    Формирует стартовое сообщение с учетом наличия акции.
    
    Returns:
        Текст стартового сообщения
    """
    base_message = (
        "😻Это бот проекта Scribo. В нём ты можешь получить курсовую или дипломную работу всего за 99⭐️!\n\n"
    )
    
    # Добавляем акцию, если она указана
    if settings.promotion_text:
        promotion_line = f"🔥В данный момент действует акция: {settings.promotion_text}\n\n"
        base_message += promotion_line
    
    base_message += "<b>Выбери желаемое действие:</b>"
    return base_message


# Функция для получения стартового сообщения (вызывается динамически)
def get_menu_message() -> str:
    """Возвращает сообщение для главного меню (то же, что и стартовое)."""
    return get_start_message()

INFO_MESSAGE = (
    "<b>Scribo Bot: Ваш умный помощник</b> 🧠\n\n"
    "Scribo — это уникальный бот на базе GPT, созданный для быстрой и качественной генерации студенческих работ.\n\n"
    "<b>Как это работает?</b>\n"
    "1. Вы присылаете тему работы.\n"
    "2. Выбираете нужные параметры (объем, тип, модель).\n"
    "3. Бот бесплатно присылает вам половину готовой работы.\n"
    "4. Если результат вас устраивает, вы оплачиваете и получаете полную версию.\n\n"
    "<b>Уникальность и конфиденциальность</b> 🔒\n"
    "Каждая работа создается с нуля и является уникальной. Мы гарантируем, что ваша работа не будет опубликована или передана третьим лицам.\n\n"
    "<b>Поддержка и обратная связь</b> ✍️\n"
    "Бот находится на этапе активной разработки. Если у вас возникнут вопросы, обращайтесь к создателю: @nikpeg.\n\n"
    "Чтобы помочь нам стать лучше, вы можете пройти небольшой опрос:\n"
    "<b>Отзывы и поддержка проекта</b> ❤️\n"
    "Почитать отзывы реальных пользователей можно здесь:\n"
    "🔗 <a href='https://docs.google.com/spreadsheets/d/1lnW0Rm5TsFEAM__c05odcggWyXn38gFtD1lvw8pQTBw/'>Таблица с отзывами</a>\n\n"
    "Если хотите поддержать проект, будем благодарны за донат:\n"
    "🔗 <a href='https://pay.cloudtips.ru/p/7a822105'>Поддержать проект</a>\n\n"
    "🔥 Приятного использования и отличных оценок!"
)


@common_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Сохраняем пользователя в базу данных
    user_created = await get_or_create_user(message.from_user.id)
    if user_created:
        await send_admin_log(message.bot, message.from_user, "Новый пользователь зарегистрирован")
    
    await message.answer(
        text=get_start_message(),
        reply_markup=get_main_menu_keyboard()
    )
    await send_admin_log(message.bot, message.from_user, "Нажал /start")

@common_router.callback_query(F.data == "main_menu")
async def handle_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=get_menu_message(), reply_markup=get_main_menu_keyboard())
    await callback.answer()
    await send_admin_log(callback.bot, callback.from_user, "Нажал кнопку 'Вернуться в меню'")


@common_router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Действие отменено. Вы возвращены в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )
    await send_admin_log(message.bot, message.from_user, "Нажал /cancel")


@common_router.message(Command("help"))
@common_router.callback_query(F.data == "info")
async def handle_info(update: Message | CallbackQuery):
    # Универсальный обработчик для /help и кнопки "О Scribo"
    if isinstance(update, Message):
        await update.answer(text=INFO_MESSAGE, reply_markup=get_back_to_menu_keyboard(), disable_web_page_preview=True)
        await send_admin_log(update.bot, update.from_user, "Нажал /help")
    else:
        await update.message.edit_text(text=INFO_MESSAGE, reply_markup=get_back_to_menu_keyboard(), disable_web_page_preview=True)
        await update.answer()
        await send_admin_log(update.bot, update.from_user, "Нажал кнопку 'Узнать о Scribo'")


@common_router.callback_query(F.data == "generate_work")
async def handle_generate_work(callback: CallbackQuery, state: FSMContext):
    """Обработчик, запускающий процесс создания работы."""
    await state.set_state(OrderStates.GET_THEME)

    # Выбираем случайный пример из настроек
    random_example = random.choice(settings.sample_works)

    # Формируем новый текст сообщения
    text = (
        "✨<b>Введи название нужной тебе работы!</b>✨\n\n"
        f"📝Пример: <code>{random_example}</code>"
    )

    await callback.message.edit_text(text=text)
    await callback.answer()
    await send_admin_log(callback.bot, callback.from_user, "Нажал кнопку 'Сгенерировать работу' (0)")
