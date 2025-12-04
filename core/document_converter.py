"""
Модуль для конвертации документов между различными форматами.
"""

import asyncio
import os
import re
from typing import Tuple


async def compile_latex_to_pdf(tex_content: str, output_dir: str, filename: str) -> Tuple[bool, str]:
    """
    Асинхронно компилирует LaTeX в PDF.
    Запускает pdflatex дважды для корректной генерации содержания и ссылок.
    
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
            if file_size > 1000:  # Минимальный размер PDF (1KB)
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
        return False, f"Exception during LaTeX compilation: {str(e)}"


async def convert_tex_to_docx(tex_content: str, output_dir: str, filename: str) -> Tuple[bool, str]:
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
        
        stdout, stderr = await pandoc_process.communicate()
        
        if pandoc_process.returncode == 0 and os.path.exists(docx_file):
            # Удаляем временный файл
            try:
                os.remove(tex_file)
            except:
                pass
            return True, docx_file
            
    except Exception as e:
        # pandoc не найден или не работает, пробуем LibreOffice
        pass
    
    # Если pandoc не сработал, пробуем LibreOffice через ODT
    return await _convert_via_libreoffice(tex_content, output_dir, filename)


async def _convert_via_libreoffice(tex_content: str, output_dir: str, filename: str) -> Tuple[bool, str]:
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
                
                stdout, stderr = await process.communicate()
                
                # Переименовываем результат
                txt_docx = os.path.join(output_dir, f"{filename}_temp.docx")
                if process.returncode == 0 and os.path.exists(txt_docx):
                    try:
                        os.rename(txt_docx, docx_file)
                        os.remove(txt_file)
                        return True, docx_file
                    except:
                        pass
                
                # Очищаем временные файлы
                try:
                    os.remove(txt_file)
                    if os.path.exists(txt_docx):
                        os.remove(txt_docx)
                except:
                    pass
                    
        except Exception as e:
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
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
    
    return clean_text