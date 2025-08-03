"""
Модуль для отправки файлов пользователям и администраторам.
"""

import os
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


async def send_error_log_to_admin(bot: Bot, order_id: int, error: Exception) -> None:
    """
    Отправляет лог об ошибке администратору.
    
    Args:
        bot: Экземпляр бота
        order_id: ID заказа
        error: Исключение с ошибкой
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
            await send_admin_log(
                bot, 
                fake_user, 
                f"🚨 <b>Ошибка генерации работы</b>\n"
                f"  <b>Заказ:</b> #{order_id}\n"
                f"  <b>Тема:</b> {order_info['theme'][:100]}...\n"
                f"  <b>Ошибка:</b> {str(error)[:200]}..."
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