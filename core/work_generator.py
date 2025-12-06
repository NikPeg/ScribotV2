"""
Основной модуль для асинхронной генерации курсовых работ.
"""

import contextlib
import os
import shutil
import tempfile
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from core.content_generator import (
    WorkContentParams,
    generate_simple_work_content,
    generate_work_content_stepwise,
    generate_work_plan,
)
from core.document_converter import (
    compile_latex_to_pdf,
    convert_pdf_to_docx,
    create_partial_pdf_with_qr,
)
from core.file_sender import (
    send_error_log_to_admin,
    send_generated_files_to_user,
    send_tex_file_to_admin,
)
from core.latex_template import create_latex_document
from core.page_calculator import (
    count_pages_in_text,
    count_total_pages_in_document,
    parse_work_plan,
    validate_work_plan,
)
from core.settings import calculate_price
from db.database import get_order_info, save_full_tex, update_order_status
from gpt.assistant import clear_conversation


@dataclass
class ProgressUpdateParams:
    """Параметры для обновления прогресса."""
    bot: Bot
    chat_id: int
    message_id: int
    stage: int
    description: str
    total_stages: int = 6


@dataclass
class SimpleWorkGenerationParams:
    """Параметры для генерации простой работы."""
    order_id: int
    model_name: str
    theme: str
    work_type: str
    bot: Bot
    chat_id: int
    message_id_to_edit: int
    total_stages: int


@dataclass
class LargeWorkGenerationParams:
    """Параметры для генерации большой работы."""
    order_id: int
    model_name: str
    theme: str
    pages: int
    work_type: str
    bot: Bot
    chat_id: int
    message_id_to_edit: int
    total_stages: int


@dataclass
class CompileAndSendParams:
    """Параметры для компиляции и отправки файлов."""
    full_tex: str
    order_id: int
    theme: str
    pages: int
    bot: Bot
    chat_id: int
    message_id_to_edit: int
    temp_dir: str
    filename: str
    model_name: str
    user_id: int


# Исключение для ошибок компиляции LaTeX
class LaTeXCompilationError(Exception):
    """Исключение для ошибок компиляции LaTeX с полным текстом ошибки."""
    def __init__(self, error_details: str):
        self.error_details = error_details
        super().__init__("LaTeX compilation failed")

# Для "прогресс-бара"
READY_SYMBOL = "🟦"
UNREADY_SYMBOL = "⬜️"

# Константы
SMALL_WORK_PAGES = 2  # Количество страниц для малых работ (используется упрощенная генерация)


async def _generate_simple_work(params: SimpleWorkGenerationParams) -> str:
    """Генерирует простую работу (1-2 страницы) без плана и оглавления."""
    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, 1, "Генерирую текст работы...", params.total_stages))
    content = await generate_simple_work_content(params.order_id, params.model_name, params.theme, params.work_type)
    
    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, 2, "Формирую LaTeX документ...", params.total_stages))
    full_tex = create_latex_document(params.theme, content, include_toc=False)
    
    content_pages = count_pages_in_text(content)
    total_pages = count_total_pages_in_document(content, 0)
    print(f"Generated simple work: {content_pages:.1f} pages of content, {total_pages:.1f} total pages")
    
    return full_tex


async def _generate_large_work(params: LargeWorkGenerationParams) -> str:
    """Генерирует большую работу с планом и оглавлением."""
    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, 1, "Составляю план работы...", params.total_stages))
    
    # Генерируем план с валидацией (до 3 попыток)
    MAX_PLAN_ATTEMPTS = 3
    plans = []
    for attempt in range(MAX_PLAN_ATTEMPTS):
        plan = await generate_work_plan(params.order_id, params.model_name, params.theme, params.pages, params.work_type)
        is_valid, items_count = validate_work_plan(plan, params.pages)
        plans.append((plan, items_count))
        
        if is_valid:
            print(f"План валиден: {items_count} пунктов (минимум: {max(1, params.pages // 3)})")
            break
        
        print(f"Попытка {attempt + 1}: план невалиден - {items_count} пунктов (минимум: {max(1, params.pages // 3)})")
        if attempt < MAX_PLAN_ATTEMPTS - 1:
            await _update_progress(
                ProgressUpdateParams(
                    params.bot, params.chat_id, params.message_id_to_edit, 1,
                    f"Перегенерирую план... (попытка {attempt + 2}/{MAX_PLAN_ATTEMPTS})", params.total_stages
                )
            )
    
    # Выбираем план с максимальным количеством пунктов
    plan, items_count = max(plans, key=lambda x: x[1])
    print(f"Выбран план с {items_count} пунктами из {len(plans)} попыток")

    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, 2, "Генерирую содержание по главам...", params.total_stages))
    
    async def content_progress_callback(description: str, progress: int):
        stage_progress = 2 + (progress / 100)
        await _update_progress_detailed(params.bot, params.chat_id, params.message_id_to_edit, stage_progress, description)
    
    content_params = WorkContentParams(
        order_id=params.order_id,
        model_name=params.model_name,
        theme=params.theme,
        pages=params.pages,
        work_type=params.work_type,
        plan_text=plan,
        progress_callback=content_progress_callback
    )
    content = await generate_work_content_stepwise(content_params)
    
    try:
        chapters = parse_work_plan(plan)
        num_chapters = len(chapters)
    except Exception:
        num_chapters = 0
    
    content_pages = count_pages_in_text(content)
    total_pages = count_total_pages_in_document(content, num_chapters)
    print(f"Generated content: {content_pages:.1f} pages of content, {total_pages:.1f} total pages (target: {params.pages})")

    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, 3, "Формирую LaTeX документ...", params.total_stages))
    return create_latex_document(params.theme, content, include_toc=True)


async def _compile_and_send_files(params: CompileAndSendParams) -> None:
    """Компилирует LaTeX в PDF/DOCX и отправляет файлы пользователю."""
    tex_path = os.path.join(params.temp_dir, f"{params.filename}.tex")
    
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(params.full_tex)

    await send_tex_file_to_admin(params.bot, params.order_id, tex_path, params.theme)

    if params.pages == SMALL_WORK_PAGES:
        current_stage = 3
        total_stages = 5
    else:
        current_stage = 4
        total_stages = 6
    
    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, current_stage, "Компилирую PDF...", total_stages))
    success, result = await compile_latex_to_pdf(params.full_tex, params.temp_dir, params.filename)
    if not success:
        raise LaTeXCompilationError(result)
    
    full_pdf_path = result

    # Рассчитываем цену
    price = calculate_price(params.model_name)
    
    # Создаем ссылку на оплату
    payment_url = await params.bot.create_invoice_link(
        title=f"Полная версия работы: {params.theme[:50]}",
        description=f"Оплата за полную версию работы. Заказ #{params.order_id}",
        payload=str(params.order_id),  # Передаем order_id в payload для обработки платежа
        provider_token="",  # Для Stars не нужен provider_token
        currency="XTR",  # XTR - валюта Telegram Stars
        prices=[{"label": "Полная версия работы", "amount": price}],  # amount в звездочках (для Stars минимальная единица = 1 звездочка)
    )
    
    # Создаем частичный PDF с QR-кодами
    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, current_stage, "Создаю частичную версию...", total_stages))
    success, partial_pdf_path = await create_partial_pdf_with_qr(
        full_pdf_path=full_pdf_path,
        payment_url=payment_url,
        user_id=params.user_id,
        temp_dir=params.temp_dir,
        output_filename=params.filename
    )
    
    if not success:
        print(f"Предупреждение: не удалось создать частичный PDF: {partial_pdf_path}")
        # В случае ошибки отправляем полный PDF
        pdf_path = full_pdf_path
    else:
        pdf_path = partial_pdf_path

    current_stage += 1
    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, current_stage, "Конвертирую в DOCX...", total_stages))
    # Конвертируем частичный PDF в DOCX, а не полный
    success, result = await convert_pdf_to_docx(pdf_path, params.temp_dir, params.filename)
    docx_path = result if success else None
    if not success:
        print(f"Предупреждение: не удалось создать DOCX файл: {result}")

    current_stage += 1
    await _update_progress(ProgressUpdateParams(params.bot, params.chat_id, params.message_id_to_edit, current_stage, "Отправляю результат...", total_stages))
    files_sent = await send_generated_files_to_user(params.bot, params.chat_id, pdf_path, docx_path, params.theme)

    await params.bot.edit_message_text(
        text=f"{READY_SYMBOL * 10}\n✅ Генерация завершена успешно!",
        chat_id=params.chat_id,
        message_id=params.message_id_to_edit
    )
    
    final_message = (
        f"🎉 Поздравляю! Ваша работа успешно сгенерирована!\n\n"
        f"📁 Отправлено файлов: {files_sent}\n\n"
        f"💡 Для получения полной версии работы произведите оплату {price} ⭐"
    )
    if docx_path is None:
        final_message += "\n\n⚠️ DOCX файл не создан (требуется LibreOffice)"
    
    # Создаем кнопку с ссылкой на оплату
    payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"💳 Оплатить {price} ⭐",
            url=payment_url
        )
    ]])
    
    await params.bot.send_message(
        chat_id=params.chat_id,
        text=final_message,
        reply_markup=payment_keyboard
    )


async def _handle_generation_error(
    e: Exception,
    order_id: int,
    bot: Bot,
    chat_id: int,
    message_id_to_edit: int
) -> None:
    """Обрабатывает ошибки генерации и уведомляет пользователя и администратора."""
    await update_order_status(order_id, 'failed')
    
    is_latex_error = isinstance(e, LaTeXCompilationError)
    await send_error_log_to_admin(bot, order_id, e, is_latex_error=is_latex_error)
    
    if is_latex_error:
        user_message = (
            "⚠️ Произошла ошибка при компиляции документа.\n\n"
            "Администратор бота уже уведомлен и скоро пришлет вам работу."
        )
    else:
        user_message = (
            "❌ Произошла ошибка во время генерации.\n\n"
            "Администратор бота уже уведомлен и скоро пришлет вам работу."
        )
    
    print(f"Error in generate_work_async: {e}")
    if is_latex_error:
        print(f"LaTeX compilation error details: {e.error_details}")
    
    try:
        await bot.edit_message_text(
            text=f"{READY_SYMBOL * 2}{UNREADY_SYMBOL * 8}\n❌ Ошибка генерации",
            chat_id=chat_id,
            message_id=message_id_to_edit
        )
        await bot.send_message(chat_id, user_message)
    except Exception as send_error:
        print(f"Failed to send error message: {send_error}")
        with contextlib.suppress(Exception):
            await bot.send_message(chat_id, "⚠️ Произошла ошибка. Администратор бота уже уведомлен и скоро пришлет вам работу.")


async def generate_work_async(
        order_id: int,
        model_name: str,
        bot: Bot,
        chat_id: int,
        message_id_to_edit: int
):
    """
    Основная асинхронная функция генерации работы.
    Полная реализация с генерацией файлов и отправкой пользователю.
    
    Args:
        order_id: ID заказа в базе данных
        model_name: Название модели GPT
        bot: Экземпляр бота Telegram
        chat_id: ID чата пользователя
        message_id_to_edit: ID сообщения для редактирования прогресса
    """
    temp_dir = None
    try:
        await update_order_status(order_id, 'generating')
        
        order_info = await get_order_info(order_id)
        if not order_info:
            raise Exception("Заказ не найден в базе данных")
        
        theme = order_info['theme']
        pages = order_info['pages']
        work_type = order_info['work_type']
        user_id = order_info['user_id']

        if pages == SMALL_WORK_PAGES:
            total_stages = 5
            simple_params = SimpleWorkGenerationParams(
                order_id=order_id,
                model_name=model_name,
                theme=theme,
                work_type=work_type,
                bot=bot,
                chat_id=chat_id,
                message_id_to_edit=message_id_to_edit,
                total_stages=total_stages
            )
            full_tex = await _generate_simple_work(simple_params)
        else:
            total_stages = 6
            large_params = LargeWorkGenerationParams(
                order_id=order_id,
                model_name=model_name,
                theme=theme,
                pages=pages,
                work_type=work_type,
                bot=bot,
                chat_id=chat_id,
                message_id_to_edit=message_id_to_edit,
                total_stages=total_stages
            )
            full_tex = await _generate_large_work(large_params)
        
        await save_full_tex(order_id, full_tex)

        temp_dir = tempfile.mkdtemp()
        filename = f"coursework_{order_id}"
        
        compile_params = CompileAndSendParams(
            full_tex=full_tex,
            order_id=order_id,
            theme=theme,
            pages=pages,
            bot=bot,
            chat_id=chat_id,
            message_id_to_edit=message_id_to_edit,
            temp_dir=temp_dir,
            filename=filename,
            model_name=model_name,
            user_id=user_id
        )
        await _compile_and_send_files(compile_params)

        await update_order_status(order_id, 'completed')

    except Exception as e:
        await _handle_generation_error(e, order_id, bot, chat_id, message_id_to_edit)
    
    finally:
        clear_conversation(order_id)
        
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                print(f"Failed to cleanup temp directory: {cleanup_error}")


async def _update_progress(params: ProgressUpdateParams) -> None:
    """
    Обновляет прогресс-бар в сообщении.
    
    Args:
        params: Параметры обновления прогресса
    """
    bot = params.bot
    chat_id = params.chat_id
    message_id = params.message_id
    stage = params.stage
    description = params.description
    total_stages = params.total_stages
    # Вычисляем количество символов прогресса (масштабируем к 10 символам)
    progress_symbols = int((stage / total_stages) * 10)
    progress_symbols = min(10, max(0, progress_symbols))
    
    progress_text = (
        f"{READY_SYMBOL * progress_symbols}{UNREADY_SYMBOL * (10 - progress_symbols)}\n"
        f"🤖 Этап {stage}/{total_stages}: {description}"
    )
    await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id)


async def _update_progress_detailed(bot: Bot, chat_id: int, message_id: int, stage: float, description: str) -> None:
    """
    Обновляет прогресс-бар с дробными этапами для детального отображения.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        message_id: ID сообщения для редактирования
        stage: Номер текущего этапа (может быть дробным)
        description: Описание текущего этапа
    """
    stage_int = int(stage)
    progress_symbols = int(stage * 10 / 6)  # Масштабируем к 10 символам
    progress_symbols = min(10, max(0, progress_symbols))
    
    progress_text = (
        f"{READY_SYMBOL * progress_symbols}{UNREADY_SYMBOL * (10 - progress_symbols)}\n"
        f"🤖 Этап {stage_int}/6: {description}"
    )
    
    try:
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id)
    except Exception as e:
        # Игнорируем ошибки обновления прогресса, чтобы не прерывать генерацию
        print(f"Failed to update progress: {e}")
