"""
Модуль для отправки файлов пользователям и администраторам.
"""

import os
import html
from aiogram import Bot
from aiogram.types import FSInputFile

from core.settings import settings
from utils.admin_logger import send_admin_log
from db.database import get_order_info


async def send_tex_file_to_admin(bot: Bot, order_id: int, tex_path: str, theme: str) -> None:
    """
    Отправляет .tex файл администратору для отладки.
    
    Args:
        bot: Экземпляр бота
        order_id: ID заказа
        tex_path: Путь к .tex файлу
        theme: Тема работы
    """
    try:
        tex_file = FSInputFile(tex_path, filename=f"coursework_{order_id}.tex")
        await bot.send_document(
            chat_id=settings.admin_id,
            document=tex_file,
            caption=f"📄 LaTeX файл для заказа #{order_id}\n\nТема: {theme[:100]}"
        )
    except Exception as admin_error:
        print(f"Failed to send tex file to admin: {admin_error}")


async def send_generated_files_to_user(bot: Bot, chat_id: int, pdf_path: str, docx_path: str, theme: str) -> int:
    """
    Отправляет сгенерированные файлы пользователю.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата пользователя
        pdf_path: Путь к PDF файлу
        docx_path: Путь к DOCX файлу (может быть None)
        theme: Тема работы
    
    Returns:
        Количество отправленных файлов
    """
    files_sent = 0
    
    # Отправляем PDF
    if os.path.exists(pdf_path):
        safe_filename = _create_safe_filename(theme)
        pdf_file = FSInputFile(pdf_path, filename=f"{safe_filename}.pdf")
        await bot.send_document(
            chat_id=chat_id,
            document=pdf_file,
            caption="📄 PDF версия вашей работы"
        )
        files_sent += 1
    
    # Отправляем DOCX если удалось создать
    if docx_path and os.path.exists(docx_path):
        safe_filename = _create_safe_filename(theme)
        docx_file = FSInputFile(docx_path, filename=f"{safe_filename}.docx")
        await bot.send_document(
            chat_id=chat_id,
            document=docx_file,
            caption="📝 DOCX версия для редактирования"
        )
        files_sent += 1
    
    return files_sent


async def send_error_log_to_admin(bot: Bot, order_id: int, error: Exception, is_latex_error: bool = False) -> None:
    """
    Отправляет лог об ошибке администратору.
    
    Args:
        bot: Экземпляр бота
        order_id: ID заказа
        error: Исключение с ошибкой
        is_latex_error: Флаг, указывающий что это ошибка компиляции LaTeX
    """
    try:
        order_info = await get_order_info(order_id)
        if order_info:
            # Создаем фиктивного пользователя для лога
            class FakeUser:
                def __init__(self, user_id):
                    self.id = user_id
                    self.full_name = f"User {user_id}"
                    self.username = None
            
            fake_user = FakeUser(order_info['user_id'])
            
            # Максимальная длина сообщения в Telegram (с запасом для HTML тегов)
            MAX_MESSAGE_LENGTH = 4000
            
            if is_latex_error and hasattr(error, 'error_details'):
                # Для ошибок компиляции LaTeX отправляем полный текст
                error_details = error.error_details
                
                # Формируем заголовок сообщения
                header = (
                    f"🚨 <b>Ошибка компиляции LaTeX</b>\n"
                    f"  <b>Заказ:</b> #{order_id}\n"
                    f"  <b>Тема:</b> {order_info['theme'][:100]}\n\n"
                    f"<b>Полный текст ошибки pdfTeX:</b>\n\n"
                )
                
                # Вычисляем доступное место для текста ошибки
                available_length = MAX_MESSAGE_LENGTH - len(header) - 50  # Запас для форматирования
                
                if len(error_details) <= available_length:
                    # Если ошибка помещается в одно сообщение
                    full_message = header + f"<pre>{html.escape(error_details)}</pre>"
                    await send_admin_log(bot, fake_user, full_message)
                else:
                    # Отправляем заголовок отдельно
                    await send_admin_log(bot, fake_user, header)
                    
                    # Разбиваем текст ошибки на части
                    chunk_size = MAX_MESSAGE_LENGTH - 100  # Запас для форматирования
                    escaped_details = html.escape(error_details)
                    
                    for i in range(0, len(escaped_details), chunk_size):
                        chunk = escaped_details[i:i + chunk_size]
                        chunk_message = f"<pre>{chunk}</pre>"
                        if i + chunk_size < len(escaped_details):
                            chunk_message += "\n\n<i>(продолжение следует...)</i>"
                        
                        await send_admin_log(bot, fake_user, chunk_message)
            else:
                # Для других ошибок - краткое сообщение
                error_text = str(error)
                if len(error_text) > 500:
                    error_text = error_text[:500] + "..."
                
                await send_admin_log(
                    bot, 
                    fake_user, 
                    f"🚨 <b>Ошибка генерации работы</b>\n"
                    f"  <b>Заказ:</b> #{order_id}\n"
                    f"  <b>Тема:</b> {order_info['theme'][:100]}\n"
                    f"  <b>Ошибка:</b> {html.escape(error_text)}"
                )
    except Exception as admin_error:
        print(f"Failed to send error log to admin: {admin_error}")


def _create_safe_filename(theme: str) -> str:
    """
    Создает безопасное имя файла из темы работы.
    
    Args:
        theme: Тема работы
    
    Returns:
        Безопасное имя файла
    """
    return "".join(c for c in theme if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]