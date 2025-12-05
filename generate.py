"""
Скрипт для генерации тестовой работы без запуска Telegram бота.
Используется для тестирования и отладки генерации документов.
"""

import asyncio
import os
import tempfile
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from db.database import init_db, create_order, update_order_status, save_full_tex, get_order_info
from core.content_generator import generate_work_plan, generate_work_content_stepwise
from core.latex_template import create_latex_document
from core.document_converter import compile_latex_to_pdf, convert_tex_to_docx
from core.page_calculator import count_pages_in_text, count_total_pages_in_document, parse_work_plan
from gpt.assistant import init_conversation, clear_conversation, TEST_MODEL_NAME


async def generate_test_work(
    theme: str,
    pages: int = 2,
    work_type: str = "курсовая",
    model_name: str = TEST_MODEL_NAME,
    output_dir: str = None
):
    """
    Генерирует тестовую работу без использования Telegram бота.
    
    Args:
        theme: Тема работы
        pages: Количество страниц
        work_type: Тип работы
        model_name: Название модели (по умолчанию TEST для тестовых данных)
        output_dir: Директория для сохранения файлов (по умолчанию текущая)
    """
    order_id = None
    temp_dir = None
    
    try:
        # Инициализируем БД
        await init_db()
        
        # Создаем заказ
        order_id = await create_order(
            user_id=999999,  # Тестовый user_id
            theme=theme,
            pages=pages,
            work_type=work_type,
            gpt_model=model_name
        )
        
        print(f"📝 Создан заказ #{order_id}")
        print(f"   Тема: {theme}")
        print(f"   Страниц: {pages}")
        print(f"   Тип: {work_type}")
        print(f"   Модель: {model_name}")
        print()
        
        # Инициализируем беседу
        init_conversation(order_id, theme)
        
        # Обновляем статус
        await update_order_status(order_id, 'generating')
        
        # --- Этап 1: Составление плана ---
        print("📋 Этап 1/5: Составляю план работы...")
        plan = await generate_work_plan(order_id, model_name, theme, pages, work_type)
        print(f"   ✓ План составлен ({len(plan)} символов)")
        print()
        
        # --- Этап 2: Генерация содержания ---
        print("✍️  Этап 2/5: Генерирую содержание по главам...")
        
        async def content_progress_callback(description: str, progress: int):
            print(f"   → {description} ({progress}%)")
        
        content = await generate_work_content_stepwise(
            order_id, model_name, theme, pages, work_type, plan, content_progress_callback
        )
        
        # Подсчитываем фактическое количество страниц
        try:
            chapters = parse_work_plan(plan)
            num_chapters = len(chapters)
        except Exception:
            num_chapters = 0
        
        content_pages = count_pages_in_text(content)
        total_pages = count_total_pages_in_document(content, num_chapters)
        print(f"   ✓ Содержание сгенерировано: {content_pages:.1f} стр. контента, {total_pages:.1f} стр. всего")
        print()
        
        # --- Этап 3: Формирование LaTeX документа ---
        print("📄 Этап 3/5: Формирую LaTeX документ...")
        full_tex = create_latex_document(theme, content)
        
        # Сохраняем tex в БД
        await save_full_tex(order_id, full_tex)
        print(f"   ✓ LaTeX документ создан ({len(full_tex)} символов)")
        print()
        
        # Определяем директорию для сохранения
        if output_dir is None:
            output_dir = os.getcwd()
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # Создаем временную директорию для компиляции
        temp_dir = tempfile.mkdtemp()
        filename = f"test_work_{order_id}"
        tex_path = os.path.join(temp_dir, f"{filename}.tex")
        
        # Записываем tex файл
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(full_tex)
        
        # Сохраняем tex файл в выходную директорию
        output_tex_path = os.path.join(output_dir, f"{filename}.tex")
        with open(output_tex_path, 'w', encoding='utf-8') as f:
            f.write(full_tex)
        print(f"   ✓ .tex файл сохранен: {output_tex_path}")
        
        # --- Этап 4: Компиляция в PDF ---
        print("📦 Этап 4/5: Компилирую PDF...")
        success, result = await compile_latex_to_pdf(full_tex, temp_dir, filename)
        if success:
            pdf_path = result
            # Копируем PDF в выходную директорию
            output_pdf_path = os.path.join(output_dir, f"{filename}.pdf")
            import shutil
            shutil.copy2(pdf_path, output_pdf_path)
            print(f"   ✓ PDF скомпилирован: {output_pdf_path}")
        else:
            print(f"   ⚠️  Ошибка компиляции PDF: {result}")
            output_pdf_path = None
        print()
        
        # --- Этап 5: Конвертация в DOCX ---
        print("📝 Этап 5/5: Конвертирую в DOCX...")
        success, result = await convert_tex_to_docx(full_tex, temp_dir, filename)
        if success:
            docx_path = result
            # Копируем DOCX в выходную директорию
            output_docx_path = os.path.join(output_dir, f"{filename}.docx")
            import shutil
            shutil.copy2(docx_path, output_docx_path)
            print(f"   ✓ DOCX создан: {output_docx_path}")
        else:
            print(f"   ⚠️  DOCX не создан: {result}")
            output_docx_path = None
        print()
        
        # Обновляем статус
        await update_order_status(order_id, 'completed')
        
        print("=" * 60)
        print("✅ Генерация завершена успешно!")
        print("=" * 60)
        print(f"📁 Файлы сохранены в: {output_dir}")
        if output_tex_path:
            print(f"   • {os.path.basename(output_tex_path)}")
        if output_pdf_path:
            print(f"   • {os.path.basename(output_pdf_path)}")
        if output_docx_path:
            print(f"   • {os.path.basename(output_docx_path)}")
        print()
        print(f"📊 Статистика:")
        print(f"   • Контент: {content_pages:.1f} страниц")
        print(f"   • Всего: {total_pages:.1f} страниц (цель: {pages})")
        print()
        
        return {
            'order_id': order_id,
            'tex_path': output_tex_path,
            'pdf_path': output_pdf_path,
            'docx_path': output_docx_path,
            'content_pages': content_pages,
            'total_pages': total_pages
        }
        
    except Exception as e:
        if order_id:
            await update_order_status(order_id, 'failed')
        print(f"❌ Ошибка генерации: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    finally:
        # Очищаем историю беседы
        if order_id:
            clear_conversation(order_id)
        
        # Очищаем временные файлы
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                print(f"⚠️  Не удалось очистить временную директорию: {cleanup_error}")


async def main():
    """Основная функция для запуска скрипта."""
    # Параметры по умолчанию
    theme = "Искусственный интеллект в современном образовании"
    pages = 2
    work_type = "курсовая"
    model_name = TEST_MODEL_NAME  # Используем тестовый режим
    
    # Можно изменить параметры через аргументы командной строки
    if len(sys.argv) > 1:
        theme = sys.argv[1]
    if len(sys.argv) > 2:
        pages = int(sys.argv[2])
    if len(sys.argv) > 3:
        work_type = sys.argv[3]
    if len(sys.argv) > 4:
        model_name = sys.argv[4]
    
    print("=" * 60)
    print("🚀 Генератор тестовых работ")
    print("=" * 60)
    print()
    
    await generate_test_work(
        theme=theme,
        pages=pages,
        work_type=work_type,
        model_name=model_name
    )


if __name__ == "__main__":
    asyncio.run(main())

