from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery

from core import OrderStates
from keyboards import get_pages_keyboard, get_work_type_keyboard, get_model_keyboard, get_back_to_menu_keyboard

order_router = Router()

@order_router.message(StateFilter(None), F.text)
async def handle_direct_theme(message: Message, state: FSMContext):
    """
    Этот хендлер ловит любое текстовое сообщение от пользователя,
    если он не находится ни в каком состоянии (StateFilter(None)).
    Он воспринимает это сообщение как тему для работы.
    """
    await state.update_data(theme=message.text)
    await message.answer(
        text="Тему принял. Теперь выберите желаемый объем работы:",
        reply_markup=get_pages_keyboard()
    )
    await state.set_state(OrderStates.GET_PAGES)


@order_router.message(StateFilter(OrderStates.GET_THEME))
async def handle_theme(message: Message, state: FSMContext):
    await state.update_data(theme=message.text)
    await message.answer(
        text="Тему принял. Теперь выберите желаемый объем работы:",
        reply_markup=get_pages_keyboard()
    )
    await state.set_state(OrderStates.GET_PAGES)


@order_router.callback_query(StateFilter(OrderStates.GET_PAGES), F.data.startswith("pages:"))
async def handle_pages(callback: CallbackQuery, state: FSMContext):
    pages = callback.data.split(":")[1]
    await state.update_data(pages=pages)
    await callback.message.edit_text(
        text="Отлично! Укажите тип работы:",
        reply_markup=get_work_type_keyboard()
    )
    await state.set_state(OrderStates.GET_TYPE)
    await callback.answer()


@order_router.callback_query(StateFilter(OrderStates.GET_TYPE), F.data == "back_to_pages")
async def back_to_pages(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Выберите желаемый объем работы:",
        reply_markup=get_pages_keyboard()
    )
    await state.set_state(OrderStates.GET_PAGES)
    await callback.answer()


@order_router.callback_query(StateFilter(OrderStates.GET_TYPE), F.data.startswith("type:"))
async def handle_work_type(callback: CallbackQuery, state: FSMContext):
    work_type = callback.data.split(":")[1]
    await state.update_data(work_type=work_type)
    await callback.message.edit_text(
        text="Почти готово! Выберите модель для генерации:",
        reply_markup=get_model_keyboard()
    )
    await state.set_state(OrderStates.GET_MODEL)
    await callback.answer()


@order_router.callback_query(StateFilter(OrderStates.GET_MODEL), F.data == "back_to_type")
async def back_to_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Укажите тип работы:",
        reply_markup=get_work_type_keyboard()
    )
    await state.set_state(OrderStates.GET_TYPE)
    await callback.answer()


@order_router.callback_query(StateFilter(OrderStates.GET_MODEL), F.data.startswith("model:"))
async def handle_model(callback: CallbackQuery, state: FSMContext):
    model = callback.data.split(":")[1]
    await state.update_data(model=model)

    user_data = await state.get_data()

    summary_text = (
        "✅ Ваш заказ принят!\n\n"
        f"<b>Тема:</b> {user_data.get('theme')}\n"
        f"<b>Объем:</b> ~{user_data.get('pages')} страниц\n"
        f"<b>Тип:</b> {user_data.get('work_type')}\n"
        f"<b>Модель:</b> {user_data.get('model')}\n"
    )

    await callback.message.edit_text(text=summary_text, parse_mode="HTML")
    await callback.answer("Заказ подтвержден")

    await callback.message.answer(
        text="⏳ Начинаю генерацию... Это может занять несколько минут.\n\n"
             "<i>(На данном этапе это сообщение-заглушка)</i>",
        parse_mode="HTML"
    )

    await callback.message.answer(
        text="Вы можете вернуться в главное меню.",
        reply_markup=get_back_to_menu_keyboard()
    )

    await state.clear()


@order_router.message(StateFilter(OrderStates.GET_PAGES, OrderStates.GET_TYPE, OrderStates.GET_MODEL))
async def handle_wrong_input_in_fsm(message: Message):
    await message.answer(
        text="Пожалуйста, используйте кнопки для выбора опции, а не вводите текст."
    )
