"""
Основной модуль для асинхронной генерации курсовых работ.
"""

import contextlib
import os
import shutil
import tempfile

from aiogram import Bot

from core.content_generator import generate_work_content_stepwise, generate_work_plan
from core.document_converter import compile_latex_to_pdf, convert_tex_to_docx
from core.file_sender import (
    send_error_log_to_admin,
    send_generated_files_to_user,
    send_tex_file_to_admin,
)
from core.latex_template import create_latex_document
from core.page_calculator import count_pages_in_text, count_total_pages_in_document, parse_work_plan
from db.database import get_order_info, save_full_tex, update_order_status
from gpt.assistant import clear_conversation


# Исключение для ошибок компиляции LaTeX
class LaTeXCompilationError(Exception):
    """Исключение для ошибок компиляции LaTeX с полным текстом ошибки."""
    def __init__(self, error_details: str):
        self.error_details = error_details
        super().__init__("LaTeX compilation failed")

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

        # Для работ 1-2 страницы используем упрощенную генерацию без плана и оглавления
        if pages == 2:
            total_stages = 5  # Для малых работ: 1-генерация, 2-формирование, 3-компиляция, 4-конвертация, 5-отправка
            
            # --- Этап 1: Генерация простой работы ---
            await _update_progress(bot, chat_id, message_id_to_edit, 1, "Генерирую текст работы...", total_stages)
            from core.content_generator import generate_simple_work_content
            content = await generate_simple_work_content(order_id, model_name, theme, work_type)
            
            # --- Этап 2: Формирование LaTeX документа (без оглавления) ---
            await _update_progress(bot, chat_id, message_id_to_edit, 2, "Формирую LaTeX документ...", total_stages)
            full_tex = create_latex_document(theme, content, include_toc=False)
            
            content_pages = count_pages_in_text(content)
            total_pages = count_total_pages_in_document(content, 0)  # Без глав для малых работ
            print(f"Generated simple work: {content_pages:.1f} pages of content, {total_pages:.1f} total pages (target: {pages})")
        else:
            total_stages = 6  # Для больших работ: 1-план, 2-генерация, 3-формирование, 4-компиляция, 5-конвертация, 6-отправка
            # --- Этап 1: Составление плана ---
            await _update_progress(bot, chat_id, message_id_to_edit, 1, "Составляю план работы...", total_stages)
            plan = await generate_work_plan(order_id, model_name, theme, pages, work_type)

            # --- Этап 2: Пошаговая генерация содержания с контролем объема ---
            await _update_progress(bot, chat_id, message_id_to_edit, 2, "Генерирую содержание по главам...", total_stages)
            
            # Создаем callback для обновления прогресса генерации
            async def content_progress_callback(description: str, progress: int):
                # Прогресс от 2 до 3 этапа (20% - 30%)
                stage_progress = 2 + (progress / 100)
                await _update_progress_detailed(bot, chat_id, message_id_to_edit, stage_progress, description)
            
            content = await generate_work_content_stepwise(
                order_id, model_name, theme, pages, work_type, plan, content_progress_callback
            )
            
            # Подсчитываем фактическое количество страниц
            # Парсим план для определения количества глав
            try:
                chapters = parse_work_plan(plan)
                num_chapters = len(chapters)
            except Exception:
                num_chapters = 0
            
            content_pages = count_pages_in_text(content)
            total_pages = count_total_pages_in_document(content, num_chapters)
            print(f"Generated content: {content_pages:.1f} pages of content, {total_pages:.1f} total pages (target: {pages})")

            # --- Этап 3: Формирование LaTeX документа ---
            await _update_progress(bot, chat_id, message_id_to_edit, 3, "Формирую LaTeX документ...", total_stages)
            full_tex = create_latex_document(theme, content, include_toc=True)
        
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

        # Определяем номер этапа в зависимости от типа работы
        if pages == 2:
            # Для малых работ этапы: 1-генерация, 2-формирование, 3-компиляция, 4-конвертация, 5-отправка
            current_stage = 3
            total_stages = 5
        else:
            # Для больших работ этапы: 1-план, 2-генерация, 3-формирование, 4-компиляция, 5-конвертация, 6-отправка
            current_stage = 4
            total_stages = 6
        
        # --- Этап 4 (или 3 для малых работ): Компиляция в PDF ---
        await _update_progress(bot, chat_id, message_id_to_edit, current_stage, "Компилирую PDF...", total_stages)
        success, result = await compile_latex_to_pdf(full_tex, temp_dir, filename)
        if not success:
            raise LaTeXCompilationError(result)
        
        pdf_path = result

        # --- Этап 5 (или 4 для малых работ): Конвертация в DOCX ---
        current_stage += 1
        await _update_progress(bot, chat_id, message_id_to_edit, current_stage, "Конвертирую в DOCX...", total_stages)
        success, result = await convert_tex_to_docx(full_tex, temp_dir, filename)
        if not success:
            # Если конвертация не удалась, продолжаем без DOCX
            print(f"Предупреждение: не удалось создать DOCX файл: {result}")
            docx_path = None
        else:
            docx_path = result

        # --- Этап 6 (или 5 для малых работ): Отправка файлов ---
        current_stage += 1
        await _update_progress(bot, chat_id, message_id_to_edit, current_stage, "Отправляю результат...", total_stages)
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
        
        # Проверяем, является ли это ошибкой компиляции LaTeX
        is_latex_error = isinstance(e, LaTeXCompilationError)
        
        # Отправляем лог об ошибке админу (с полным текстом для LaTeX ошибок)
        await send_error_log_to_admin(bot, order_id, e, is_latex_error=is_latex_error)
        
        # Сообщение для пользователя
        if is_latex_error:
            # Для ошибок компиляции LaTeX - дружелюбное сообщение
            user_message = (
                "⚠️ Произошла ошибка при компиляции документа.\n\n"
                "Администратор бота уже уведомлен и скоро пришлет вам работу."
            )
        else:
            # Для других ошибок - общее сообщение
            user_message = (
                "❌ Произошла ошибка во время генерации.\n\n"
                "Администратор бота уже уведомлен и скоро пришлет вам работу."
            )
        
        # Полная ошибка в логи
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
            # Если и короткое сообщение не отправляется, отправляем минимальное
            with contextlib.suppress(Exception):
                await bot.send_message(chat_id, "⚠️ Произошла ошибка. Администратор бота уже уведомлен и скоро пришлет вам работу.")
    
    finally:
        # Очищаем историю беседы для заказа
        clear_conversation(order_id)
        
        # Очищаем временные файлы
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                print(f"Failed to cleanup temp directory: {cleanup_error}")


async def _update_progress(bot: Bot, chat_id: int, message_id: int, stage: int, description: str, total_stages: int = 6) -> None:
    """
    Обновляет прогресс-бар в сообщении.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        message_id: ID сообщения для редактирования
        stage: Номер текущего этапа
        description: Описание текущего этапа
        total_stages: Общее количество этапов (по умолчанию 6)
    """
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
