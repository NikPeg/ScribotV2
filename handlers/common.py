from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from core import OrderStates
from keyboards import get_main_menu_keyboard, get_pages_keyboard

# Этот роутер будет обрабатывать команды, не связанные с процессом заказа
common_router = Router()

# Тексты сообщений лучше вынести в отдельный файл, но для первого этапа оставим здесь
START_MESSAGE = (
    "👋 Привет! Я Scribo — твой персональный помощник для создания курсовых работ. \n\n"
    "Просто пришли мне тему, и я сгенерирую для тебя уникальную работу с помощью ChatGPT."
)
MENU_MESSAGE = "🏠 Главное меню"


@common_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    await message.answer(
        text=START_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )


@common_router.message(Command("menu"))
@common_router.callback_query(F.data == "main_menu")
async def handle_menu(update: Message | CallbackQuery, state: FSMContext):
    """Обработчик команды /menu и колбэка main_menu."""
    await state.clear()

    # Определяем, как отвечать: новым сообщением или редактированием старого
    if isinstance(update, Message):
        await update.answer(text=MENU_MESSAGE, reply_markup=get_main_menu_keyboard())
    else:
        # update is a CallbackQuery
        await update.message.edit_text(text=MENU_MESSAGE, reply_markup=get_main_menu_keyboard())
        await update.answer() # Закрываем "часики" на кнопке


@common_router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext):
    """Обработчик команды /cancel для сброса состояния FSM."""
    await state.clear()
    await message.answer(
        "Действие отменено. Вы возвращены в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )


@common_router.callback_query(F.data == "generate_work")
async def handle_generate_work(callback: CallbackQuery, state: FSMContext):
    """Обработчик, запускающий процесс создания работы."""
    await state.set_state(OrderStates.GET_THEME)
    await callback.message.edit_text(
        text="Отлично! 🚀\n\nПришлите мне тему вашей будущей работы."
    )
    await callback.answer()
