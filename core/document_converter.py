"""
Модуль для конвертации документов между различными форматами.
"""

import asyncio
import contextlib
import os
import re

import qrcode
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# Константы
MIN_PDF_SIZE_BYTES = 1000  # Минимальный размер PDF файла (1KB)


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


async def convert_pdf_to_docx(pdf_path: str, output_dir: str, filename: str) -> tuple[bool, str]:
    """
    Конвертирует PDF в DOCX используя LibreOffice.
    
    Args:
        pdf_path: Путь к PDF файлу
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
                # Конвертируем PDF в DOCX
                process = await asyncio.create_subprocess_exec(
                    cmd,
                    '--headless',
                    '--convert-to', 'docx',
                    '--outdir', output_dir,
                    pdf_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                _stdout, _stderr = await process.communicate()
                
                # LibreOffice создает файл с именем исходного PDF, но с расширением .docx
                pdf_basename = os.path.basename(pdf_path)
                pdf_name_without_ext = os.path.splitext(pdf_basename)[0]
                generated_docx = os.path.join(output_dir, f"{pdf_name_without_ext}.docx")
                
                if process.returncode == 0 and os.path.exists(generated_docx):
                    # Переименовываем в нужное имя
                    if generated_docx != docx_file:
                        with contextlib.suppress(OSError):
                            os.rename(generated_docx, docx_file)
                    return True, docx_file
                    
        except Exception:
            continue
    
    return False, "LibreOffice не найден или не может конвертировать PDF в DOCX"


async def convert_tex_to_docx(tex_content: str, output_dir: str, filename: str) -> tuple[bool, str]:
    """
    Конвертирует TEX напрямую в DOCX используя pandoc или LibreOffice.
    
    Args:
        tex_content: Содержимое LaTeX файла
        output_dir: Директория для выходных файлов
        filename: Имя файла без расширения
    
    Returns:
        Tuple[bool, str]: (успех, путь_к_файлу_или_ошибка)
    """
    docx_file = os.path.join(output_dir, f"{filename}.docx")
    
    # Сначала пробуем pandoc (более надежно для LaTeX -> DOCX)
    try:
        # Создаем временный tex файл
        tex_file = os.path.join(output_dir, f"{filename}_temp.tex")
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(tex_content)
        
        # Пробуем pandoc
        pandoc_process = await asyncio.create_subprocess_exec(
            'pandoc',
            tex_file,
            '-o', docx_file,
            '--from=latex',
            '--to=docx',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        _stdout, _stderr = await pandoc_process.communicate()
        
        if pandoc_process.returncode == 0 and os.path.exists(docx_file):
            # Удаляем временный файл
            with contextlib.suppress(OSError):
                os.remove(tex_file)
            return True, docx_file
            
    except Exception:
        # pandoc не найден или не работает, пробуем LibreOffice
        pass
    
    # Если pandoc не сработал, пробуем LibreOffice через ODT
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
    
    img = qr.make_image(fill_color="black", back_color="white")
    qr_path = os.path.join(temp_dir, f"qr_code_{user_id}.png")
    img.save(qr_path)
    
    return qr_path


def _create_text_image(text: str, font_size: int, width_px: int, user_id: int, temp_dir: str) -> str:
    """
    Создает изображение с текстом для вставки в PDF (для поддержки кириллицы).
    
    Args:
        text: Текст для отображения
        font_size: Размер шрифта
        width_px: Ширина изображения в пикселях
        user_id: ID пользователя (для уникального имени файла)
        temp_dir: Временная директория
    
    Returns:
        Путь к файлу с изображением текста
    """
    # Создаем изображение с прозрачным фоном
    img = Image.new('RGBA', (width_px, 100), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Пробуем использовать системный шрифт с поддержкой кириллицы
    try:
        # Пробуем использовать системные шрифты
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',  # macOS
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
            'C:/Windows/Fonts/arial.ttf',  # Windows
        ]
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except Exception:
                    continue
        
        if font is None:
            # Используем стандартный шрифт
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    # Получаем размеры текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Создаем новое изображение с правильным размером
    img = Image.new('RGBA', (text_width + 20, text_height + 20), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Рисуем текст
    draw.text((10, 10), text, fill=(0, 0, 0, 255), font=font)
    
    # Сохраняем изображение
    text_img_path = os.path.join(temp_dir, f"text_{user_id}_{hash(text)}.png")
    img.save(text_img_path)
    
    return text_img_path


def _create_qr_code_pdf_page(payment_url: str, price: int, user_id: int, temp_dir: str) -> str:
    """
    Создает PDF страницу с QR-кодом и текстом об оплате.
    
    Args:
        payment_url: Ссылка на оплату
        price: Цена в звездочках
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
    qr_y = (height - qr_size) / 2 + 30 * mm  # Немного выше центра для текста
    
    # Вставляем QR-код
    c.drawImage(qr_path, qr_x, qr_y, width=qr_size, height=qr_size)
    
    # Создаем изображения с текстом для поддержки кириллицы
    text = "Для получения полной версии произведите оплату по ссылке"
    text_img_path = _create_text_image(text, 16, int(width), user_id, temp_dir)
    
    # Вставляем текст как изображение
    text_y = qr_y - 25 * mm
    text_img = Image.open(text_img_path)
    text_height = 20 * mm  # Высота текста
    text_width_img = (text_height / text_img.height) * text_img.width
    c.drawImage(text_img_path, (width - text_width_img) / 2, text_y, width=text_width_img, height=text_height)
    
    # Добавляем цену
    price_text = f"Цена: {price} ⭐"
    price_img_path = _create_text_image(price_text, 14, int(width), user_id, temp_dir)
    price_y = text_y - 18 * mm
    price_img = Image.open(price_img_path)
    price_height = 15 * mm
    price_width_img = (price_height / price_img.height) * price_img.width
    c.drawImage(price_img_path, (width - price_width_img) / 2, price_y, width=price_width_img, height=price_height)
    
    c.save()
    
    return pdf_path


async def create_partial_pdf_with_qr(  # noqa: PLR0913
    full_pdf_path: str,
    payment_url: str,
    price: int,
    user_id: int,
    temp_dir: str,
    output_filename: str
) -> tuple[bool, str]:
    """
    Создает частичный PDF: первая половина страниц из оригинала + страницы с QR-кодами.
    
    Args:
        full_pdf_path: Путь к полному PDF файлу
        payment_url: Ссылка на оплату
        price: Цена в звездочках
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
        qr_page_path = _create_qr_code_pdf_page(payment_url, price, user_id, temp_dir)
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
