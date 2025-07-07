from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from core import OrderStates
from keyboards import get_main_menu_keyboard, get_back_to_menu_keyboard

common_router = Router()

START_MESSAGE = (
    "😻Это бот проекта Scribo. В нём ты можешь получить курсовую или дипломную работу всего за 99 рублей!\n\n"
    "🔥В данный момент действует акция: <b>бесплатная</b> генерация половины работы!\n\n"
    "<b>Выбери желаемое действие:</b>"
)
MENU_MESSAGE = "🏠 Главное меню"

INFO_MESSAGE = (
    "<b>Scribo Bot: Ваш умный помощник</b> 🧠\n\n"
    "Scribo — это уникальный бот на базе ChatGPT, созданный для быстрой и качественной генерации студенческих работ.\n\n"
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
    await message.answer(
        text=START_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

@common_router.callback_query(F.data == "main_menu")
async def handle_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=MENU_MESSAGE, reply_markup=get_main_menu_keyboard())
    await callback.answer()


@common_router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Действие отменено. Вы возвращены в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )


@common_router.message(Command("help"))
@common_router.callback_query(F.data == "info")
async def handle_info(update: Message | CallbackQuery):
    # Универсальный обработчик для /help и кнопки "О Scribo"
    if isinstance(update, Message):
        await update.answer(text=INFO_MESSAGE, reply_markup=get_back_to_menu_keyboard(), disable_web_page_preview=True)
    else:
        await update.message.edit_text(text=INFO_MESSAGE, reply_markup=get_back_to_menu_keyboard(), disable_web_page_preview=True)
        await update.answer()


@common_router.callback_query(F.data == "generate_work")
async def handle_generate_work(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.GET_THEME)
    await callback.message.edit_text(
        text="Отлично! 🚀\n\nПришлите мне тему вашей будущей работы."
    )
    await callback.answer()
