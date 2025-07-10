import asyncio
from aiogram import Bot

from db.database import update_order_status
from gpt.assistant import ask_assistant

# Для "прогресс-бара"
READY_SYMBOL = "🟦"
UNREADY_SYMBOL = "⬜️"


async def generate_work_async(
        order_id: int,
        thread_id: str,
        model_name: str,
        bot: Bot,
        chat_id: int,
        message_id_to_edit: int
):
    """
    Основная асинхронная функция генерации работы.
    (На данном этапе это заглушка, демонстрирующая пошаговое взаимодействие с GPT)
    """
    try:
        await update_order_status(order_id, 'generating')

        # --- Этап 1: Составление плана ---
        progress_text = (
            f"{READY_SYMBOL * 1}{UNREADY_SYMBOL * 9}\n"
            "🤖 Этап 1/3: Составляю план работы..."
        )
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id_to_edit)

        plan_prompt = "Составь подробный план для курсовой работы на тему, которую я указал ранее. План должен состоять из введения, 3-4 глав (каждая с 2-3 подразделами) и заключения."
        plan = await ask_assistant(thread_id, plan_prompt, model_name)

        # --- Этап 2: Написание введения ---
        progress_text = (
            f"{READY_SYMBOL * 4}{UNREADY_SYMBOL * 6}\n"
            "✅ План готов. Этап 2/3: Пишу введение...\n\n"
            "<i>Краткий план:</i>" # Показываем пользователю часть плана
        )
        await bot.edit_message_text(
            text=f"{progress_text}\n<code>{plan[:1000]}</code>",
            chat_id=chat_id,
            message_id=message_id_to_edit
        )

        intro_prompt = "Отлично, теперь напиши введение для этой работы в формате TeX. Объем около 300-400 слов."
        introduction = await ask_assistant(thread_id, intro_prompt, model_name)

        # --- Этап 3: Завершение (пока заглушка) ---
        progress_text = (
            f"{READY_SYMBOL * 10}{UNREADY_SYMBOL * 0}\n"
            "✅ Введение готово. Этап 3/3: Генерация завершена!"
        )
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id_to_edit)

        # Информационное сообщение о результате (пока заглушка)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🎉 Поздравляю! Ваша работа сгенерирована.\n\n"
                "(Это заглушка. На следующих этапах здесь будет отправка готовых файлов PDF и DOCX)"
            )
        )

        # --- Обновляем статус в БД ---
        await update_order_status(order_id, 'completed')

    except Exception as e:
        await update_order_status(order_id, 'failed')
        error_message = f"Произошла ошибка во время генерации: {e}"
        print(error_message) # Лог в консоль для отладки
        await bot.send_message(chat_id, error_message)
