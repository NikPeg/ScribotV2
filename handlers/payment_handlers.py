"""
Обработчики для работы с платежами через Telegram Stars.
"""

import logging
import os
import tempfile

from aiogram import Bot, F, Router
from aiogram.types import Message, PreCheckoutQuery, SuccessfulPayment

from core.document_converter import compile_latex_to_pdf, convert_tex_to_docx
from core.file_sender import send_generated_files_to_user
from db.database import get_order_info
from utils.admin_logger import send_admin_log

logger = logging.getLogger(__name__)

payment_router = Router()


@payment_router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """
    Обрабатывает запрос перед оплатой (pre_checkout_query).
    Подтверждает оплату, если заказ существует.
    """
    try:
        order_id = int(pre_checkout_query.invoice_payload)
        order_info = await get_order_info(order_id)
        
        if order_info and order_info.get('full_tex'):
            # Заказ существует и имеет полный текст - подтверждаем оплату
            await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
            logger.info(f"Pre-checkout подтвержден для заказа #{order_id}")
        else:
            # Заказ не найден или не имеет полного текста - отклоняем оплату
            await bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Заказ не найден или работа еще не сгенерирована"
            )
            logger.warning(f"Pre-checkout отклонен для заказа #{order_id}: заказ не найден")
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка при обработке pre_checkout_query: {e}")
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=False,
            error_message="Ошибка обработки запроса"
        )


@payment_router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):  # noqa: PLR0915
    """
    Обрабатывает успешную оплату.
    Генерирует полную версию работы и отправляет пользователю.
    """
    try:
        payment: SuccessfulPayment = message.successful_payment
        
        # Извлекаем order_id из payload
        order_id = int(payment.invoice_payload)
        
        # Получаем информацию о заказе
        order_info = await get_order_info(order_id)
        if not order_info:
            await message.answer(
                "❌ Ошибка: заказ не найден. Пожалуйста, обратитесь в поддержку."
            )
            logger.error(f"Заказ #{order_id} не найден при обработке платежа")
            return
        
        if not order_info.get('full_tex'):
            await message.answer(
                "❌ Ошибка: полный текст работы не найден. Пожалуйста, обратитесь в поддержку."
            )
            logger.error(f"Полный текст для заказа #{order_id} не найден")
            return
        
        user_id = order_info['user_id']
        theme = order_info['theme']
        full_tex = order_info['full_tex']
        
        # Уведомляем администратора об оплате СРАЗУ после оплаты
        admin_message = (
            f"💰 <b>Оплата получена</b>\n\n"
            f"  <b>Пользователь:</b> {message.from_user.full_name} (@{message.from_user.username or 'нет'})\n"
            f"  <b>User ID:</b> {user_id}\n"
            f"  <b>Заказ:</b> #{order_id}\n"
            f"  <b>Тема:</b> {theme[:100]}\n"
            f"  <b>Сумма:</b> {payment.total_amount} ⭐"
        )
        await send_admin_log(bot, message.from_user, admin_message)
        
        # Уведомляем пользователя о начале генерации
        processing_message = await message.answer(
            "⏳ Обрабатываю оплату... Генерирую полную версию работы..."
        )
        
        # Создаем временную директорию для генерации файлов
        temp_dir = tempfile.mkdtemp()
        filename = f"coursework_full_{order_id}"
        
        try:
            # Компилируем полный PDF
            success, pdf_path = await compile_latex_to_pdf(full_tex, temp_dir, filename)
            if not success:
                # Отправляем ошибку конвертации PDF администратору
                error_details = pdf_path if pdf_path else "Неизвестная ошибка (пустое сообщение об ошибке)"
                admin_error_message = (
                    f"🚨 <b>Ошибка при компиляции PDF</b>\n\n"
                    f"  <b>Заказ:</b> #{order_id}\n"
                    f"  <b>Пользователь:</b> {user_id}\n"
                    f"  <b>Тема:</b> {theme[:100]}\n"
                    f"  <b>Временная директория:</b> {temp_dir}\n"
                    f"  <b>Ошибка:</b> {error_details[:2000]}"
                )
                await send_admin_log(bot, message.from_user, admin_error_message)
                raise Exception(f"Ошибка компиляции PDF: {pdf_path}")
            
            # Конвертируем в DOCX (опционально)
            logger.info(f"Начинаю конвертацию DOCX для заказа #{order_id}")
            success_docx, docx_path = await convert_tex_to_docx(full_tex, temp_dir, filename)
            docx_path = docx_path if success_docx else None
            
            # Если DOCX не удалось создать, уведомляем администратора
            if not success_docx:
                error_details = docx_path if docx_path else "Неизвестная ошибка (пустое сообщение об ошибке)"
                logger.error(
                    f"Ошибка при создании DOCX для заказа #{order_id}: {error_details}",
                    exc_info=True
                )
                
                # Формируем детальное сообщение для администратора
                admin_error_message = (
                    f"🚨 <b>Ошибка при создании DOCX файла</b>\n\n"
                    f"  <b>Заказ:</b> #{order_id}\n"
                    f"  <b>Пользователь:</b> {user_id}\n"
                    f"  <b>Тема:</b> {theme[:100]}\n"
                    f"  <b>Временная директория:</b> {temp_dir}\n"
                    f"  <b>Ошибка:</b> {error_details[:1000]}"
                )
                await send_admin_log(bot, message.from_user, admin_error_message)
            
            # Отправляем файлы пользователю
            files_sent = await send_generated_files_to_user(
                bot, user_id, pdf_path, docx_path, theme
            )
            
            # Удаляем сообщение о обработке
            await processing_message.delete()
            
            # Формируем сообщение об успешной оплате
            success_message = (
                f"✅ Оплата успешно обработана!\n\n"
                f"📁 Отправлено файлов: {files_sent}\n\n"
            )
            
            # Если DOCX не был создан, добавляем предупреждение
            if not success_docx:
                success_message += (
                    "⚠️ Ошибка при создании DOCX файла. Администратор уже уведомлен и скоро отправит вам работу.\n\n"
                )
            
            success_message += "🎉 Спасибо за оплату! Полная версия работы отправлена."
            await message.answer(success_message)
            
            logger.info(f"Успешная оплата обработана для заказа #{order_id}, пользователь {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при генерации полной версии для заказа #{order_id}: {e}")
            await processing_message.delete()
            await message.answer(
                "❌ Произошла ошибка при генерации полной версии работы. "
                "Администратор уведомлен и скоро пришлет вам работу."
            )
            
            # Уведомляем администратора об ошибке (если еще не было отправлено сообщение об ошибке PDF)
            error_message = (
                f"🚨 <b>Ошибка при обработке оплаты</b>\n\n"
                f"  <b>Заказ:</b> #{order_id}\n"
                f"  <b>Пользователь:</b> {user_id}\n"
                f"  <b>Тема:</b> {theme[:100]}\n"
                f"  <b>Ошибка:</b> {str(e)[:2000]}"
            )
            await send_admin_log(bot, message.from_user, error_message)
        
        finally:
            # Очищаем временные файлы
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Не удалось очистить временную директорию: {cleanup_error}")
    
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка при обработке successful_payment: {e}")
        await message.answer(
            "❌ Ошибка обработки платежа. Пожалуйста, обратитесь в поддержку."
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке платежа: {e}")
        await message.answer(
            "❌ Произошла неожиданная ошибка. Администратор уведомлен."
        )

