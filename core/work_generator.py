import asyncio
import os
import tempfile
import subprocess
from pathlib import Path
from aiogram import Bot
from aiogram.types import FSInputFile

from db.database import update_order_status, save_full_tex, get_order_info
from gpt.assistant import ask_assistant

# Для "прогресс-бара"
READY_SYMBOL = "🟦"
UNREADY_SYMBOL = "⬜️"

# Шаблон LaTeX документа
LATEX_TEMPLATE = r"""
\documentclass[12pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T2A]{{fontenc}}
\usepackage[russian]{{babel}}
\usepackage{{geometry}}
\usepackage{{setspace}}
\usepackage{{indentfirst}}
\usepackage{{amsmath}}
\usepackage{{amsfonts}}
\usepackage{{amssymb}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}

\geometry{{left=3cm,right=1.5cm,top=2cm,bottom=2cm}}
\onehalfspacing
\setlength{{\parindent}}{{1.25cm}}

\begin{{document}}

\begin{{titlepage}}
\centering
\vspace*{{2cm}}
{{\Large\textbf{{МИНИСТЕРСТВО ОБРАЗОВАНИЯ И НАУКИ РФ}}}}\\[0.5cm]
{{\large Федеральное государственное бюджетное\\
образовательное учреждение высшего образования}}\\[0.5cm]
{{\Large\textbf{{РОССИЙСКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ}}}}\\[2cm]

{{\large Факультет информационных технологий}}\\[0.5cm]
{{\large Кафедра программной инженерии}}\\[3cm]

{{\Large\textbf{{КУРСОВАЯ РАБОТА}}}}\\[0.5cm]
{{\large по дисциплине}}\\[0.3cm]
{{\large Информационные технологии}}\\[1cm]

{{\Large\textbf{{Тема: {theme}}}}}\\[3cm]

\begin{{flushright}}
Выполнил: студент группы ИТ-21\\
Иванов И.И.\\[1cm]
Проверил: к.т.н., доцент\\
Петров П.П.
\end{{flushright}}

\vfill
{{\large Москва 2024}}
\end{{titlepage}}

\newpage
\tableofcontents
\newpage

{content}

\end{{document}}
"""

async def generate_full_work_content(thread_id: str, model_name: str, theme: str, pages: int, work_type: str) -> str:
    """
    Генерирует полное содержание работы через GPT.
    """
    # Промпт для генерации полной работы
    full_work_prompt = f"""
Напиши полную {work_type.lower()} на тему "{theme}" объемом примерно {pages} страниц.

Структура должна включать:
1. Введение (1-2 страницы)
2. Основная часть (3-4 главы, каждая 2-3 страницы)
3. Заключение (1-2 страницы)
4. Список литературы

ВАЖНЫЕ требования к форматированию:
- Текст должен быть в формате LaTeX (без преамбулы и \\begin{{document}})
- Используй команды \\section{{}} для глав, \\subsection{{}} для подразделов
- НЕ используй длинные строки текста - разбивай абзацы на короткие строки (максимум 80 символов)
- После каждого предложения делай перенос строки
- Включи формулы, таблицы или рисунки где уместно
- Текст должен быть академическим и структурированным
- Добавь реальные источники в список литературы

Начни прямо с введения:
"""
    
    return await ask_assistant(thread_id, full_work_prompt, model_name)

async def compile_latex_to_pdf(tex_content: str, output_dir: str, filename: str) -> tuple[bool, str]:
    """
    Асинхронно компилирует LaTeX в PDF.
    Возвращает (успех, путь_к_файлу_или_ошибка).
    """
    tex_file = os.path.join(output_dir, f"{filename}.tex")
    pdf_file = os.path.join(output_dir, f"{filename}.pdf")
    
    try:
        # Записываем tex файл
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(tex_content)
        
        # Асинхронно запускаем pdflatex
        process = await asyncio.create_subprocess_exec(
            'pdflatex',
            '-interaction=nonstopmode',
            '-output-directory', output_dir,
            tex_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=output_dir
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(pdf_file):
            return True, pdf_file
        else:
            error_msg = f"LaTeX compilation failed. Return code: {process.returncode}\n"
            error_msg += f"STDOUT: {stdout.decode('utf-8', errors='ignore')}\n"
            error_msg += f"STDERR: {stderr.decode('utf-8', errors='ignore')}"
            return False, error_msg
            
    except Exception as e:
        return False, f"Exception during LaTeX compilation: {str(e)}"

async def convert_pdf_to_docx(pdf_path: str, output_dir: str, filename: str) -> tuple[bool, str]:
    """
    Конвертирует PDF в DOCX используя libreoffice.
    Возвращает (успех, путь_к_файлу_или_ошибка).
    """
    docx_file = os.path.join(output_dir, f"{filename}.docx")
    
    # Возможные пути к LibreOffice на разных системах
    libreoffice_commands = [
        'libreoffice',  # Linux/Windows в PATH
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',  # macOS стандартная установка
        '/usr/bin/libreoffice',  # Linux системная установка
        'soffice'  # Альтернативное имя
    ]
    
    for cmd in libreoffice_commands:
        try:
            # Проверяем доступность команды
            check_process = await asyncio.create_subprocess_exec(
                cmd, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await check_process.communicate()
            
            if check_process.returncode == 0:
                # Команда найдена, используем её для конвертации
                process = await asyncio.create_subprocess_exec(
                    cmd,
                    '--headless',
                    '--convert-to', 'docx',
                    '--outdir', output_dir,
                    pdf_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and os.path.exists(docx_file):
                    return True, docx_file
                else:
                    error_msg = f"PDF to DOCX conversion failed with {cmd}. Return code: {process.returncode}\n"
                    error_msg += f"STDOUT: {stdout.decode('utf-8', errors='ignore')}\n"
                    error_msg += f"STDERR: {stderr.decode('utf-8', errors='ignore')}"
                    return False, error_msg
                    
        except Exception as e:
            # Пробуем следующую команду
            continue
    
    return False, "LibreOffice not found. Tried commands: " + ", ".join(libreoffice_commands)

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
    Полная реализация с генерацией файлов и отправкой пользователю.
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
        progress_text = (
            f"{READY_SYMBOL * 1}{UNREADY_SYMBOL * 9}\n"
            "🤖 Этап 1/6: Составляю план работы..."
        )
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id_to_edit)

        plan_prompt = f"Составь подробный план для {work_type.lower()} на тему '{theme}' объемом {pages} страниц. План должен состоять из введения, 3-4 глав (каждая с 2-3 подразделами) и заключения."
        plan = await ask_assistant(thread_id, plan_prompt, model_name)

        # --- Этап 2: Генерация полного содержания ---
        progress_text = (
            f"{READY_SYMBOL * 2}{UNREADY_SYMBOL * 8}\n"
            "✅ План готов. Этап 2/6: Генерирую полное содержание работы..."
        )
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id_to_edit)

        content = await generate_full_work_content(thread_id, model_name, theme, pages, work_type)

        # --- Этап 3: Формирование LaTeX документа ---
        progress_text = (
            f"{READY_SYMBOL * 4}{UNREADY_SYMBOL * 6}\n"
            "✅ Содержание готово. Этап 3/6: Формирую LaTeX документ..."
        )
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id_to_edit)

        # Создаем полный LaTeX документ
        full_tex = LATEX_TEMPLATE.format(theme=theme, content=content)
        
        # Сохраняем tex в БД
        await save_full_tex(order_id, full_tex)

        # --- Этап 4: Компиляция в PDF ---
        progress_text = (
            f"{READY_SYMBOL * 6}{UNREADY_SYMBOL * 4}\n"
            "✅ LaTeX готов. Этап 4/6: Компилирую PDF..."
        )
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id_to_edit)

        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        filename = f"coursework_{order_id}"
        
        success, result = await compile_latex_to_pdf(full_tex, temp_dir, filename)
        if not success:
            raise Exception(f"Ошибка компиляции LaTeX: {result}")
        
        pdf_path = result

        # --- Этап 5: Конвертация в DOCX ---
        progress_text = (
            f"{READY_SYMBOL * 8}{UNREADY_SYMBOL * 2}\n"
            "✅ PDF готов. Этап 5/6: Конвертирую в DOCX..."
        )
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id_to_edit)

        success, result = await convert_pdf_to_docx(pdf_path, temp_dir, filename)
        if not success:
            # Если конвертация не удалась, продолжаем без DOCX
            print(f"Предупреждение: не удалось создать DOCX файл: {result}")
            docx_path = None
        else:
            docx_path = result

        # --- Этап 6: Отправка файлов ---
        progress_text = (
            f"{READY_SYMBOL * 10}{UNREADY_SYMBOL * 0}\n"
            "✅ Файлы готовы. Этап 6/6: Отправляю результат..."
        )
        await bot.edit_message_text(text=progress_text, chat_id=chat_id, message_id=message_id_to_edit)

        # Отправляем файлы пользователю
        files_sent = 0
        
        # Отправляем PDF
        if os.path.exists(pdf_path):
            # Безопасное имя файла
            safe_filename = "".join(c for c in theme if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
            pdf_file = FSInputFile(pdf_path, filename=f"{safe_filename}.pdf")
            await bot.send_document(
                chat_id=chat_id,
                document=pdf_file,
                caption="📄 PDF версия вашей работы"
            )
            files_sent += 1
        
        # Отправляем DOCX если удалось создать
        if docx_path and os.path.exists(docx_path):
            safe_filename = "".join(c for c in theme if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
            docx_file = FSInputFile(docx_path, filename=f"{safe_filename}.docx")
            await bot.send_document(
                chat_id=chat_id,
                document=docx_file,
                caption="📝 DOCX версия для редактирования"
            )
            files_sent += 1

        # Финальное сообщение
        await bot.edit_message_text(
            text=f"{READY_SYMBOL * 10}\n✅ Генерация завершена успешно!",
            chat_id=chat_id,
            message_id=message_id_to_edit
        )
        
        # Отправляем итоговое сообщение
        final_message = f"🎉 Поздравляю! Ваша работа успешно сгенерирована!\n\n📁 Отправлено файлов: {files_sent}"
        if docx_path is None:
            final_message += "\n\n⚠️ DOCX файл не создан (требуется LibreOffice)"
        
        await bot.send_message(chat_id=chat_id, text=final_message)

        # --- Обновляем статус в БД ---
        await update_order_status(order_id, 'completed')

    except Exception as e:
        await update_order_status(order_id, 'failed')
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
        # Очищаем временные файлы
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                print(f"Failed to cleanup temp directory: {cleanup_error}")
