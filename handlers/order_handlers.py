from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from utils.admin_logger import send_admin_log
import html
from core import OrderStates
from aiogram import Bot
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
        text="Тему принял. Теперь выберите желаемый <b>объем работы</b>:",
        reply_markup=get_pages_keyboard()
    )
    await state.set_state(OrderStates.GET_PAGES)
    log_text = f"Ввел тему напрямую: «{html.escape(message.text[:100])}»"
    await send_admin_log(message.bot, message.from_user, log_text)


@order_router.message(StateFilter(OrderStates.GET_THEME))
async def handle_theme(message: Message, state: FSMContext):
    await state.update_data(theme=message.text)
    await message.answer(
        text="Тему принял. Теперь выберите желаемый <b>объем работы</b>:",
        reply_markup=get_pages_keyboard()
    )
    await state.set_state(OrderStates.GET_PAGES)
    await send_admin_log(message.bot, message.from_user, "Выбрал тему (1)")


@order_router.callback_query(StateFilter(OrderStates.GET_PAGES), F.data.startswith("pages:"))
async def handle_pages(callback: CallbackQuery, state: FSMContext):
    pages = callback.data.split(":")[1]
    await state.update_data(pages=pages)
    await callback.message.edit_text(
        text="Отлично! Укажите <b>тип работы</b>:",
        reply_markup=get_work_type_keyboard()
    )
    await state.set_state(OrderStates.GET_TYPE)
    await callback.answer()
    await send_admin_log(callback.bot, callback.from_user, "Выбрал число страниц (2)")


@order_router.callback_query(StateFilter(OrderStates.GET_TYPE), F.data == "back_to_pages")
async def back_to_pages(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Выберите желаемый объем работы:",
        reply_markup=get_pages_keyboard()
    )
    await state.set_state(OrderStates.GET_PAGES)
    await callback.answer()
    await send_admin_log(callback.bot, callback.from_user, "Выбрал объем (3)")


@order_router.callback_query(StateFilter(OrderStates.GET_TYPE), F.data.startswith("type:"))
async def handle_work_type(callback: CallbackQuery, state: FSMContext):
    work_type = callback.data.split(":")[1]
    await state.update_data(work_type=work_type)
    await callback.message.edit_text(
        text="Почти готово! Выберите <b>модель</b> для генерации:",
        reply_markup=get_model_keyboard()
    )
    await state.set_state(OrderStates.GET_MODEL)
    await callback.answer()
    await send_admin_log(callback.bot, callback.from_user, "Выбрал тип (3)")


@order_router.callback_query(StateFilter(OrderStates.GET_MODEL), F.data == "back_to_type")
async def back_to_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Укажите <b>тип работы</b>:",
        reply_markup=get_work_type_keyboard()
    )
    await state.set_state(OrderStates.GET_TYPE)
    await callback.answer()
    await send_admin_log(callback.bot, callback.from_user, "Выбрал модель (5)")


@order_router.callback_query(StateFilter(OrderStates.GET_MODEL), F.data.startswith("model:"))
async def handle_model(callback: CallbackQuery, state: FSMContext, bot: Bot):
    model = callback.data.split(":")[1]
    await state.update_data(model=model)
    user_data = await state.get_data()
    await state.clear()

    summary_text = (
        f"<b>Тема:</b> {user_data.get('theme')}\n"
        f"<b>Объем:</b> ~{user_data.get('pages')} страниц\n"
        f"<b>Тип:</b> {user_data.get('work_type')}\n"
        f"<b>Модель:</b> {user_data.get('model')}\n"
    )
    await callback.message.edit_text(text=summary_text)

    # vvv ЭТО СООБЩЕНИЕ МЫ БУДЕМ РЕДАКТИРОВАТЬ vvv
    progress_message = await callback.message.answer(
        text="⏳ Инициализация... Готовлюсь к генерации."
    )

    order_id = await create_order(...) # ...

    thread_id = await create_thread()
    await update_order_thread_id(order_id, thread_id)

    await ask_assistant(thread_id, f"Тема моей работы: «{user_data.get('theme')}». Запомни её.", model)

    # 4. Запускаем генерацию в фоновой задаче
    asyncio.create_task(
        generate_work_async(
            order_id=order_id,
            thread_id=thread_id,
            model_name=model,
            bot=bot,
            chat_id=callback.from_user.id,
            # vvv ПЕРЕДАЕМ ID СООБЩЕНИЯ ДЛЯ РЕДАКТИРОВАНИЯ vvv
            message_id_to_edit=progress_message.message_id
        )
    )

    await callback.message.answer(
        text="Вы можете вернуться в главное меню.",
        reply_markup=get_back_to_menu_keyboard()
    )

    await state.clear()
    log_summary = (
        f"✅ <b>Завершил формирование заказа</b>\n"
        f"  <b>Тема:</b> {html.escape(user_data.get('theme'))}\n"
        f"  <b>Объем:</b> ~{user_data.get('pages')} страниц\n"
        f"  <b>Тип:</b> {user_data.get('work_type')}\n"
        f"  <b>Модель:</b> {user_data.get('model')}"
    )
    await send_admin_log(callback.bot, callback.from_user, log_summary)


@order_router.message(StateFilter(OrderStates.GET_PAGES, OrderStates.GET_TYPE, OrderStates.GET_MODEL))
async def handle_wrong_input_in_fsm(message: Message):
    await message.answer(
        text="Пожалуйста, используйте кнопки для выбора опции, а не вводите текст."
    )
    await send_admin_log(message.bot, message.from_user, f"Пользователь ввёл неожиданный текст: {message.text}")
