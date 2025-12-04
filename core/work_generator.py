"""
Основной модуль для асинхронной генерации курсовых работ.
"""

import asyncio
import os
import tempfile
import shutil
from aiogram import Bot

from db.database import update_order_status, save_full_tex, get_order_info
from core.content_generator import generate_work_plan, generate_work_content_stepwise
from core.latex_template import create_latex_document
from core.document_converter import compile_latex_to_pdf, convert_tex_to_docx
from core.file_sender import send_tex_file_to_admin, send_generated_files_to_user, send_error_log_to_admin
from core.page_calculator import count_pages_in_text
from gpt.assistant import clear_conversation

# Для "прогресс-бара"
READY_SYMBOL = "🟦"
UNREADY_SYMBOL = "⬜️"


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
        
        # Получаем информацию о заказе
        order_info = await get_order_info(order_id)
        if not order_info:
            raise Exception("Заказ не найден в базе данных")
        
        theme = order_info['theme']
        pages = order_info['pages']
        work_type = order_info['work_type']

        # --- Этап 1: Составление плана ---
        await _update_progress(bot, chat_id, message_id_to_edit, 1, "Составляю план работы...")
        plan = await generate_work_plan(order_id, model_name, theme, pages, work_type)

        # --- Этап 2: Пошаговая генерация содержания с контролем объема ---
        await _update_progress(bot, chat_id, message_id_to_edit, 2, "Генерирую содержание по главам...")
        
        # Создаем callback для обновления прогресса генерации
        async def content_progress_callback(description: str, progress: int):
            # Прогресс от 2 до 3 этапа (20% - 30%)
            stage_progress = 2 + (progress / 100)
            await _update_progress_detailed(bot, chat_id, message_id_to_edit, stage_progress, description)
        
        content = await generate_work_content_stepwise(
            order_id, model_name, theme, pages, work_type, plan, content_progress_callback
        )
        
        # Подсчитываем фактическое количество страниц
        actual_pages = count_pages_in_text(content)
        print(f"Generated content: {actual_pages:.1f} pages (target: {pages})")

        # --- Этап 3: Формирование LaTeX документа ---
        await _update_progress(bot, chat_id, message_id_to_edit, 3, "Формирую LaTeX документ...")
        full_tex = create_latex_document(theme, content)
        
        # Сохраняем tex в БД
        await save_full_tex(order_id, full_tex)

        # Создаем временную директорию и сохраняем tex файл
        temp_dir = tempfile.mkdtemp()
        filename = f"coursework_{order_id}"
        tex_path = os.path.join(temp_dir, f"{filename}.tex")
        
        # Записываем tex файл
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(full_tex)

        # Отправляем .tex файл админу для отладки (всегда, до компиляции)
        await send_tex_file_to_admin(bot, order_id, tex_path, theme)

        # --- Этап 4: Компиляция в PDF ---
        await _update_progress(bot, chat_id, message_id_to_edit, 4, "Компилирую PDF...")
        success, result = await compile_latex_to_pdf(full_tex, temp_dir, filename)
        if not success:
            raise Exception(f"Ошибка компиляции LaTeX: {result}")
        
        pdf_path = result

        # --- Этап 5: Конвертация в DOCX ---
        await _update_progress(bot, chat_id, message_id_to_edit, 5, "Конвертирую в DOCX...")
        success, result = await convert_tex_to_docx(full_tex, temp_dir, filename)
        if not success:
            # Если конвертация не удалась, продолжаем без DOCX
            print(f"Предупреждение: не удалось создать DOCX файл: {result}")
            docx_path = None
        else:
            docx_path = result

        # --- Этап 6: Отправка файлов ---
        await _update_progress(bot, chat_id, message_id_to_edit, 6, "Отправляю результат...")
        files_sent = await send_generated_files_to_user(bot, chat_id, pdf_path, docx_path, theme)

        # Финальное сообщение
        await bot.edit_message_text(
            text=f"{READY_SYMBOL * 10}\n✅ Генерация завершена успешно!",
            chat_id=chat_id,
            message_id=message_id_to_edit
        )
        
        # Отправляем итоговое сообщение
        final_message = f"🎉 Поздравляю! Ваша работа успешно сгенерирована!\n\n📁 Отправлено файлов: {files_sent}"
        if docx_path is None:
            final_message += "\n\n⚠️ DOCX файл не создан (требуется LibreOffice или Pandoc)"
        
        await bot.send_message(chat_id=chat_id, text=final_message)

        # --- Обновляем статус в БД ---
        await update_order_status(order_id, 'completed')

    except Exception as e:
        await update_order_status(order_id, 'failed')
        
        # Отправляем лог об ошибке админу
        await send_error_log_to_admin(bot, order_id, e)
        
        # Короткое сообщение об ошибке для пользователя
        error_text = str(e)[:200] + "..." if len(str(e)) > 200 else str(e)
        error_text = error_text.replace('<', '&lt;').replace('>', '&gt;')
        error_message = f"❌ Произошла ошибка во время генерации:\n\n{error_text}"
        
        # Полная ошибка в логи
        print(f"Error in generate_work_async: {e}")
        
        try:
            await bot.edit_message_text(
                text=f"{READY_SYMBOL * 2}{UNREADY_SYMBOL * 8}\n❌ Ошибка генерации",
                chat_id=chat_id,
                message_id=message_id_to_edit
            )
            await bot.send_message(chat_id, error_message)
        except Exception as send_error:
            print(f"Failed to send error message: {send_error}")
            # Если и короткое сообщение не отправляется, отправляем минимальное
            try:
                await bot.send_message(chat_id, "❌ Произошла ошибка во время генерации. Попробуйте еще раз.")
            except:
                pass
    
    finally:
        # Очищаем историю беседы для заказа
        clear_conversation(order_id)
        
        # Очищаем временные файлы
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                print(f"Failed to cleanup temp directory: {cleanup_error}")


async def _update_progress(bot: Bot, chat_id: int, message_id: int, stage: int, description: str) -> None:
    """
    Обновляет прогресс-бар в сообщении.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        message_id: ID сообщения для редактирования
        stage: Номер текущего этапа (1-6)
        description: Описание текущего этапа
    """
    progress_text = (
        f"{READY_SYMBOL * stage}{UNREADY_SYMBOL * (10 - stage)}\n"
        f"🤖 Этап {stage}/6: {description}"
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
