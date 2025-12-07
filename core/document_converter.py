"""
Модуль для конвертации документов между различными форматами.
"""

import asyncio
import contextlib
import logging
import os
import re

import qrcode
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Константы
MIN_PDF_SIZE_BYTES = 1000  # Минимальный размер PDF файла (1KB)

# Логгер для модуля
logger = logging.getLogger(__name__)


async def compile_latex_to_pdf(tex_content: str, output_dir: str, filename: str) -> tuple[bool, str]:
    """
    Асинхронно компилирует LaTeX в PDF.
    Запускает pdflatex дважды для корректной генерации содержания, ссылок и библиографии.
    
    Args:
        tex_content: Содержимое LaTeX файла
        output_dir: Директория для выходных файлов
        filename: Имя файла без расширения
    
    Returns:
        Tuple[bool, str]: (успех, путь_к_файлу_или_ошибка)
    """
    tex_file = os.path.join(output_dir, f"{filename}.tex")
    pdf_file = os.path.join(output_dir, f"{filename}.pdf")
    
    try:
        # Записываем tex файл
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(tex_content)
        
        # Первый проход pdflatex (генерирует .aux файлы)
        process1 = await asyncio.create_subprocess_exec(
            'pdflatex',
            '-interaction=nonstopmode',
            '-output-directory', output_dir,
            tex_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=output_dir
        )
        
        stdout1, stderr1 = await process1.communicate()
        
        # Второй проход pdflatex (использует .aux для содержания и ссылок)
        process2 = await asyncio.create_subprocess_exec(
            'pdflatex',
            '-interaction=nonstopmode',
            '-output-directory', output_dir,
            tex_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=output_dir
        )
        
        stdout2, stderr2 = await process2.communicate()
        
        # Проверяем результат: главное - наличие PDF файла
        # pdflatex может возвращать ненулевой код даже при успешной компиляции (warnings)
        if os.path.exists(pdf_file):
            # Проверяем размер файла - если он слишком маленький, возможно компиляция не удалась
            file_size = os.path.getsize(pdf_file)
            if file_size > MIN_PDF_SIZE_BYTES:
                return True, pdf_file
        
        # Если PDF не создан или слишком маленький - это реальная ошибка
        # Собираем полный текст ошибки без обрезки
        stdout1_text = stdout1.decode('utf-8', errors='ignore')
        stdout2_text = stdout2.decode('utf-8', errors='ignore')
        stderr1_text = stderr1.decode('utf-8', errors='ignore')
        stderr2_text = stderr2.decode('utf-8', errors='ignore')
        
        error_msg = f"LaTeX compilation failed. Return code: {process2.returncode}\n"
        if not os.path.exists(pdf_file):
            error_msg += "PDF file was not created.\n"
        else:
            error_msg += f"PDF file exists but is too small ({os.path.getsize(pdf_file)} bytes).\n"
        error_msg += f"\n=== First pass stdout ===\n{stdout1_text}\n\n"
        error_msg += f"=== First pass stderr ===\n{stderr1_text}\n\n"
        error_msg += f"=== Second pass stdout ===\n{stdout2_text}\n\n"
        error_msg += f"=== Second pass stderr ===\n{stderr2_text}"
        return False, error_msg
            
    except Exception as e:
        return False, f"Exception during LaTeX compilation: {e!s}"


async def convert_pdf_to_docx(pdf_path: str, output_dir: str, filename: str) -> tuple[bool, str]:  # noqa: PLR0912, PLR0915
    """
    Конвертирует PDF в DOCX используя LibreOffice через промежуточный формат ODT.
    LibreOffice не может напрямую конвертировать PDF в DOCX, поэтому используем ODT как промежуточный формат.
    
    Args:
        pdf_path: Путь к PDF файлу
        output_dir: Директория для выходных файлов
        filename: Имя файла без расширения
    
    Returns:
        Tuple[bool, str]: (успех, путь_к_файлу_или_ошибка)
    """
    docx_file = os.path.join(output_dir, f"{filename}.docx")
    
    # Проверяем существование PDF файла
    if not os.path.exists(pdf_path):
        error_msg = f"PDF файл не найден: {pdf_path}"
        logger.error(error_msg)
        return False, error_msg
    
    pdf_size = os.path.getsize(pdf_path)
    logger.info(f"Начинаю конвертацию PDF в DOCX через ODT: {pdf_path} (размер: {pdf_size} байт)")
    
    libreoffice_commands = [
        'libreoffice',  # Linux/Windows в PATH
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',  # macOS стандартная установка
        '/usr/bin/libreoffice',  # Linux системная установка
        'soffice'  # Альтернативное имя
    ]
    
    last_error = None
    
    for cmd in libreoffice_commands:
        try:
            logger.debug(f"Проверяю доступность команды: {cmd}")
            # Проверяем доступность команды
            check_process = await asyncio.create_subprocess_exec(
                cmd, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _check_stdout, check_stderr = await check_process.communicate()
            
            if check_process.returncode == 0:
                logger.info(f"LibreOffice найден: {cmd}")
                
                # Шаг 1: Конвертируем PDF в ODT (LibreOffice может это делать)
                pdf_basename = os.path.basename(pdf_path)
                pdf_name_without_ext = os.path.splitext(pdf_basename)[0]
                odt_file = os.path.join(output_dir, f"{pdf_name_without_ext}.odt")
                
                logger.debug(f"Шаг 1: Конвертация PDF в ODT: {cmd} --headless --convert-to odt --outdir {output_dir} {pdf_path}")
                process_odt = await asyncio.create_subprocess_exec(
                    cmd,
                    '--headless',
                    '--convert-to', 'odt',
                    '--outdir', output_dir,
                    pdf_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout_odt, stderr_odt = await process_odt.communicate()
                _stdout_odt_text = stdout_odt.decode('utf-8', errors='ignore') if stdout_odt else ""
                stderr_odt_text = stderr_odt.decode('utf-8', errors='ignore') if stderr_odt else ""
                
                logger.debug(f"PDF->ODT завершился с кодом: {process_odt.returncode}")
                if stderr_odt_text:
                    logger.debug(f"PDF->ODT stderr: {stderr_odt_text[:500]}")
                
                if process_odt.returncode != 0 or not os.path.exists(odt_file):
                    error_msg = (
                        f"Не удалось конвертировать PDF в ODT. "
                        f"Код возврата: {process_odt.returncode}, "
                        f"Файл существует: {os.path.exists(odt_file)}, "
                        f"stderr: {stderr_odt_text[:500]}"
                    )
                    logger.warning(error_msg)
                    last_error = error_msg
                    continue
                
                logger.info(f"ODT файл создан: {odt_file}")
                
                # Шаг 2: Конвертируем ODT в DOCX
                logger.debug(f"Шаг 2: Конвертация ODT в DOCX: {cmd} --headless --convert-to docx --outdir {output_dir} {odt_file}")
                process_docx = await asyncio.create_subprocess_exec(
                    cmd,
                    '--headless',
                    '--convert-to', 'docx',
                    '--outdir', output_dir,
                    odt_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout_docx, stderr_docx = await process_docx.communicate()
                stdout_docx_text = stdout_docx.decode('utf-8', errors='ignore') if stdout_docx else ""
                stderr_docx_text = stderr_docx.decode('utf-8', errors='ignore') if stderr_docx else ""
                
                logger.debug(f"ODT->DOCX завершился с кодом: {process_docx.returncode}")
                if stderr_docx_text:
                    logger.debug(f"ODT->DOCX stderr: {stderr_docx_text[:500]}")
                
                # LibreOffice создает файл с именем исходного ODT, но с расширением .docx
                generated_docx = os.path.join(output_dir, f"{pdf_name_without_ext}.docx")
                
                logger.debug(f"Ожидаемый файл: {generated_docx}, существует: {os.path.exists(generated_docx)}")
                logger.debug(f"Целевой файл: {docx_file}, существует: {os.path.exists(docx_file)}")
                
                # Удаляем промежуточный ODT файл
                with contextlib.suppress(OSError):
                    os.remove(odt_file)
                    logger.debug(f"Промежуточный ODT файл удален: {odt_file}")
                
                if process_docx.returncode == 0 and os.path.exists(generated_docx):
                    # Переименовываем в нужное имя
                    if generated_docx != docx_file:
                        try:
                            os.rename(generated_docx, docx_file)
                            logger.info(f"Файл переименован: {generated_docx} -> {docx_file}")
                        except OSError as e:
                            logger.warning(f"Не удалось переименовать файл: {e}")
                            # Пробуем использовать существующий файл
                            docx_file = generated_docx
                    
                    if os.path.exists(docx_file):
                        file_size = os.path.getsize(docx_file)
                        logger.info(f"DOCX файл успешно создан: {docx_file} (размер: {file_size} байт)")
                        return True, docx_file
                    error_msg = f"Файл {docx_file} не существует после переименования"
                    logger.error(error_msg)
                    last_error = error_msg
                else:
                    error_msg = (
                        f"LibreOffice конвертация ODT->DOCX не удалась. "
                        f"Код возврата: {process_docx.returncode}, "
                        f"Файл существует: {os.path.exists(generated_docx)}, "
                        f"stdout: {stdout_docx_text[:200]}, "
                        f"stderr: {stderr_docx_text[:200]}"
                    )
                    logger.error(error_msg)
                    last_error = error_msg
            else:
                logger.debug(f"Команда {cmd} недоступна (код возврата: {check_process.returncode})")
                check_stderr_text = check_stderr.decode('utf-8', errors='ignore') if check_stderr else ""
                last_error = f"Команда {cmd} недоступна: {check_stderr_text[:200]}"
                    
        except FileNotFoundError:
            logger.debug(f"Команда {cmd} не найдена")
            last_error = f"Команда {cmd} не найдена в PATH"
            continue
        except Exception as e:
            logger.error(f"Ошибка при попытке использовать {cmd}: {e}", exc_info=True)
            last_error = f"Ошибка при использовании {cmd}: {e!s}"
            continue
    
    error_msg = f"LibreOffice не найден или не может конвертировать PDF в DOCX. Последняя ошибка: {last_error}"
    logger.error(error_msg)
    return False, error_msg


async def convert_tex_to_docx(tex_content: str, output_dir: str, filename: str) -> tuple[bool, str]:
    """
    Конвертирует TEX в DOCX через промежуточный PDF для сохранения форматирования.
    Это гарантирует сохранение оглавления и разрывов страниц.
    
    Args:
        tex_content: Содержимое LaTeX файла
        output_dir: Директория для выходных файлов
        filename: Имя файла без расширения
    
    Returns:
        Tuple[bool, str]: (успех, путь_к_файлу_или_ошибка)
    """
    logger.info(f"Начинаю конвертацию TEX в DOCX для файла: {filename}")
    
    # Сначала компилируем LaTeX в PDF для сохранения форматирования
    logger.debug("Шаг 1: Компиляция LaTeX в PDF")
    success, pdf_path = await compile_latex_to_pdf(tex_content, output_dir, filename)
    if not success:
        logger.warning(f"Не удалось скомпилировать LaTeX в PDF: {pdf_path[:500]}")
        logger.info("Пробую прямой конверт через pandoc")
        # Если не удалось скомпилировать PDF, пробуем прямой конверт через pandoc
        return await _convert_tex_to_docx_direct(tex_content, output_dir, filename)
    
    logger.info(f"PDF успешно скомпилирован: {pdf_path}")
    
    # Конвертируем PDF в DOCX - это сохранит форматирование, TOC и разрывы страниц
    logger.debug("Шаг 2: Конвертация PDF в DOCX")
    return await convert_pdf_to_docx(pdf_path, output_dir, filename)


async def _convert_tex_to_docx_direct(tex_content: str, output_dir: str, filename: str) -> tuple[bool, str]:
    """
    Прямая конвертация TEX в DOCX через pandoc (резервный метод).
    Используется только если компиляция в PDF не удалась.
    
    Args:
        tex_content: Содержимое LaTeX файла
        output_dir: Директория для выходных файлов
        filename: Имя файла без расширения
    
    Returns:
        Tuple[bool, str]: (успех, путь_к_файлу_или_ошибка)
    """
    logger.info("Пробую прямую конвертацию TEX в DOCX через pandoc")
    docx_file = os.path.join(output_dir, f"{filename}.docx")
    
    # Сначала пробуем pandoc с улучшенными параметрами
    try:
        # Создаем временный tex файл
        tex_file = os.path.join(output_dir, f"{filename}_temp.tex")
        logger.debug(f"Создаю временный TEX файл: {tex_file}")
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(tex_content)
        
        # Пробуем pandoc с параметрами для сохранения структуры
        logger.debug(f"Запускаю pandoc: pandoc {tex_file} -o {docx_file}")
        pandoc_process = await asyncio.create_subprocess_exec(
            'pandoc',
            tex_file,
            '-o', docx_file,
            '--from=latex',
            '--to=docx',
            '--toc',  # Генерировать оглавление
            '--toc-depth=3',  # Глубина оглавления
            '--wrap=none',  # Не переносить строки
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await pandoc_process.communicate()
        stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
        stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
        
        logger.debug(f"Pandoc завершился с кодом: {pandoc_process.returncode}")
        if stdout_text:
            logger.debug(f"Pandoc stdout: {stdout_text[:500]}")
        if stderr_text:
            logger.debug(f"Pandoc stderr: {stderr_text[:500]}")
        
        if pandoc_process.returncode == 0 and os.path.exists(docx_file):
            file_size = os.path.getsize(docx_file)
            logger.info(f"DOCX успешно создан через pandoc: {docx_file} (размер: {file_size} байт)")
            # Удаляем временный файл
            with contextlib.suppress(OSError):
                os.remove(tex_file)
            return True, docx_file
        error_msg = (
            f"Pandoc конвертация не удалась. "
            f"Код возврата: {pandoc_process.returncode}, "
            f"Файл существует: {os.path.exists(docx_file)}, "
            f"stderr: {stderr_text[:500]}"
        )
        logger.warning(error_msg)
            
    except FileNotFoundError:
        logger.warning("Pandoc не найден в PATH")
    except Exception as e:
        logger.error(f"Ошибка при использовании pandoc: {e}", exc_info=True)
    
    # Если pandoc не сработал, пробуем LibreOffice через ODT
    logger.info("Pandoc не сработал, пробую LibreOffice")
    return await _convert_via_libreoffice(tex_content, output_dir, filename)


async def _convert_via_libreoffice(tex_content: str, output_dir: str, filename: str) -> tuple[bool, str]:
    """
    Конвертирует через LibreOffice как резервный метод.
    
    Args:
        tex_content: Содержимое LaTeX файла
        output_dir: Директория для выходных файлов
        filename: Имя файла без расширения
    
    Returns:
        Tuple[bool, str]: (успех, путь_к_файлу_или_ошибка)
    """
    docx_file = os.path.join(output_dir, f"{filename}.docx")
    
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
                # Создаем простой ODT файл из текста (без LaTeX команд)
                # Извлекаем только текстовое содержимое
                clean_text = _extract_text_from_latex(tex_content)
                
                # Создаем простой текстовый файл
                txt_file = os.path.join(output_dir, f"{filename}_temp.txt")
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write(clean_text)
                
                # Конвертируем TXT в DOCX
                process = await asyncio.create_subprocess_exec(
                    cmd,
                    '--headless',
                    '--convert-to', 'docx',
                    '--outdir', output_dir,
                    txt_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                _stdout, _stderr = await process.communicate()
                
                # Переименовываем результат
                txt_docx = os.path.join(output_dir, f"{filename}_temp.docx")
                if process.returncode == 0 and os.path.exists(txt_docx):
                    with contextlib.suppress(OSError):
                        os.rename(txt_docx, docx_file)
                        os.remove(txt_file)
                        return True, docx_file
                
                # Очищаем временные файлы
                with contextlib.suppress(OSError):
                    os.remove(txt_file)
                    if os.path.exists(txt_docx):
                        os.remove(txt_docx)
                    
        except Exception:
            continue
    
    return False, "Neither pandoc nor LibreOffice could convert to DOCX"


def _extract_text_from_latex(tex_content: str) -> str:
    """
    Извлекает чистый текст из LaTeX, убирая команды форматирования.
    
    Args:
        tex_content: LaTeX содержимое
    
    Returns:
        Чистый текст
    """
    # Убираем LaTeX команды и оставляем только текст
    clean_text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', tex_content)
    clean_text = re.sub(r'\\[a-zA-Z]+', '', clean_text)
    clean_text = re.sub(r'\{[^}]*\}', '', clean_text)
    clean_text = re.sub(r'\\\\', '\n', clean_text)
    return re.sub(r'\n\s*\n', '\n\n', clean_text)


def _create_qr_code_image(payment_url: str, user_id: int, temp_dir: str) -> str:
    """
    Создает QR-код из ссылки на оплату и сохраняет его во временный файл.
    
    Args:
        payment_url: Ссылка на оплату
        user_id: ID пользователя (для уникального имени файла)
        temp_dir: Временная директория
    
    Returns:
        Путь к файлу с QR-кодом
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payment_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#220d8c", back_color="white")
    qr_path = os.path.join(temp_dir, f"qr_code_{user_id}.png")
    img.save(qr_path)
    
    return qr_path


def _create_qr_code_pdf_page(payment_url: str, user_id: int, temp_dir: str) -> str:
    """
    Создает PDF страницу с QR-кодом.
    
    Args:
        payment_url: Ссылка на оплату
        user_id: ID пользователя (для уникального имени файла)
        temp_dir: Временная директория
    
    Returns:
        Путь к PDF файлу с одной страницей
    """
    # Создаем QR-код
    qr_path = _create_qr_code_image(payment_url, user_id, temp_dir)
    
    # Создаем PDF страницу
    pdf_path = os.path.join(temp_dir, f"qr_page_{user_id}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    
    # Размер QR-кода - половина ширины страницы
    qr_size = width * 0.5
    
    # Позиция QR-кода по центру страницы
    qr_x = (width - qr_size) / 2
    qr_y = (height - qr_size) / 2
    
    # Вставляем QR-код
    c.drawImage(qr_path, qr_x, qr_y, width=qr_size, height=qr_size)
    
    c.save()
    
    return pdf_path


async def create_partial_pdf_with_qr(
    full_pdf_path: str,
    payment_url: str,
    user_id: int,
    temp_dir: str,
    output_filename: str
) -> tuple[bool, str]:
    """
    Создает частичный PDF: первая половина страниц из оригинала + страницы с QR-кодами.
    
    Args:
        full_pdf_path: Путь к полному PDF файлу
        payment_url: Ссылка на оплату
        user_id: ID пользователя
        temp_dir: Временная директория
        output_filename: Имя выходного файла без расширения
    
    Returns:
        Tuple[bool, str]: (успех, путь_к_файлу_или_ошибка)
    """
    try:
        # Читаем оригинальный PDF
        reader = PdfReader(full_pdf_path)
        total_pages = len(reader.pages)
        
        if total_pages == 0:
            return False, "PDF файл не содержит страниц"
        
        # Определяем количество страниц для первой половины
        half_pages = total_pages // 2
        qr_pages_count = total_pages - half_pages
        
        # Создаем новый PDF writer
        writer = PdfWriter()
        
        # Добавляем первую половину страниц из оригинала
        for i in range(half_pages):
            writer.add_page(reader.pages[i])
        
        # Создаем страницы с QR-кодами
        qr_page_path = _create_qr_code_pdf_page(payment_url, user_id, temp_dir)
        qr_reader = PdfReader(qr_page_path)
        qr_page = qr_reader.pages[0]
        
        # Добавляем страницы с QR-кодами
        for _ in range(qr_pages_count):
            writer.add_page(qr_page)
        
        # Сохраняем частичный PDF
        partial_pdf_path = os.path.join(temp_dir, f"{output_filename}_partial.pdf")
        with open(partial_pdf_path, 'wb') as output_file:
            writer.write(output_file)
        
        return True, partial_pdf_path
        
    except Exception as e:
        return False, f"Ошибка при создании частичного PDF: {e!s}"
