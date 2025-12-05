"""
Скрипт для генерации тестовой работы без запуска Telegram бота.
Используется для тестирования и отладки генерации документов.
"""

import asyncio
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Константы для аргументов командной строки
ARG_INDEX_THEME = 1
ARG_INDEX_PAGES = 2
ARG_INDEX_WORK_TYPE = 3
ARG_INDEX_MODEL_NAME = 4

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импорты после изменения sys.path необходимы для работы скрипта
from core.content_generator import (  # noqa: E402
    WorkContentParams,
    generate_work_content_stepwise,
    generate_work_plan,
)
from core.document_converter import compile_latex_to_pdf, convert_tex_to_docx  # noqa: E402
from core.latex_template import create_latex_document  # noqa: E402
from core.page_calculator import (  # noqa: E402
    count_pages_in_text,
    count_total_pages_in_document,
    parse_work_plan,
)
from db.database import create_order, init_db, save_full_tex, update_order_status  # noqa: E402
from gpt.assistant import TEST_MODEL_NAME, clear_conversation, init_conversation  # noqa: E402


async def _setup_test_order(
    theme: str,
    pages: int,
    work_type: str,
    model_name: str
) -> int:
    """Создает тестовый заказ и инициализирует БД."""
    await init_db()
    
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
    
    init_conversation(order_id, theme)
    await update_order_status(order_id, 'generating')
    
    return order_id


async def _generate_test_content(
    order_id: int,
    model_name: str,
    theme: str,
    pages: int,
    work_type: str
) -> tuple[str, float, float]:
    """Генерирует план и содержание тестовой работы."""
    print("📋 Этап 1/5: Составляю план работы...")
    plan = await generate_work_plan(order_id, model_name, theme, pages, work_type)
    print(f"   ✓ План составлен ({len(plan)} символов)")
    print()
    
    print("✍️  Этап 2/5: Генерирую содержание по главам...")
    
    async def content_progress_callback(description: str, progress: int):
        print(f"   → {description} ({progress}%)")
    
    content_params = WorkContentParams(
        order_id=order_id,
        model_name=model_name,
        theme=theme,
        pages=pages,
        work_type=work_type,
        plan_text=plan,
        progress_callback=content_progress_callback
    )
    content = await generate_work_content_stepwise(content_params)
    
    try:
        chapters = parse_work_plan(plan)
        num_chapters = len(chapters)
    except Exception:
        num_chapters = 0
    
    content_pages = count_pages_in_text(content)
    total_pages = count_total_pages_in_document(content, num_chapters)
    print(f"   ✓ Содержание сгенерировано: {content_pages:.1f} стр. контента, {total_pages:.1f} стр. всего")
    print()
    
    print("📄 Этап 3/5: Формирую LaTeX документ...")
    full_tex = create_latex_document(theme, content)
    await save_full_tex(order_id, full_tex)
    print(f"   ✓ LaTeX документ создан ({len(full_tex)} символов)")
    print()
    
    return full_tex, content_pages, total_pages


async def _compile_test_files(
    full_tex: str,
    output_dir: str,
    temp_dir: str,
    filename: str
) -> tuple[str | None, str | None, str | None]:
    """Компилирует LaTeX в PDF/DOCX и сохраняет файлы."""
    output_tex_path = os.path.join(output_dir, f"{filename}.tex")
    with open(output_tex_path, 'w', encoding='utf-8') as f:
        f.write(full_tex)
    print(f"   ✓ .tex файл сохранен: {output_tex_path}")
    
    print("📦 Этап 4/5: Компилирую PDF...")
    success, result = await compile_latex_to_pdf(full_tex, temp_dir, filename)
    if success:
        output_pdf_path = os.path.join(output_dir, f"{filename}.pdf")
        shutil.copy2(result, output_pdf_path)
        print(f"   ✓ PDF скомпилирован: {output_pdf_path}")
    else:
        print(f"   ⚠️  Ошибка компиляции PDF: {result}")
        output_pdf_path = None
    print()
    
    print("📝 Этап 5/5: Конвертирую в DOCX...")
    success, result = await convert_tex_to_docx(full_tex, temp_dir, filename)
    if success:
        output_docx_path = os.path.join(output_dir, f"{filename}.docx")
        shutil.copy2(result, output_docx_path)
        print(f"   ✓ DOCX создан: {output_docx_path}")
    else:
        print(f"   ⚠️  DOCX не создан: {result}")
        output_docx_path = None
    print()
    
    return output_tex_path, output_pdf_path, output_docx_path


@dataclass
class TestResultsParams:
    """Параметры для вывода результатов тестовой генерации."""
    output_dir: str
    output_tex_path: str | None
    output_pdf_path: str | None
    output_docx_path: str | None
    content_pages: float
    total_pages: float
    pages: int


def _print_test_results(params: TestResultsParams) -> None:
    """Выводит результаты генерации."""
    print("=" * 60)
    print("✅ Генерация завершена успешно!")
    print("=" * 60)
    print(f"📁 Файлы сохранены в: {params.output_dir}")
    if params.output_tex_path:
        print(f"   • {os.path.basename(params.output_tex_path)}")
    if params.output_pdf_path:
        print(f"   • {os.path.basename(params.output_pdf_path)}")
    if params.output_docx_path:
        print(f"   • {os.path.basename(params.output_docx_path)}")
    print()
    print("📊 Статистика:")
    print(f"   • Контент: {params.content_pages:.1f} страниц")
    print(f"   • Всего: {params.total_pages:.1f} страниц (цель: {params.pages})")
    print()


async def generate_test_work(
    theme: str,
    pages: int = 2,
    work_type: str = "курсовая",
    model_name: str = TEST_MODEL_NAME,
    output_dir: str | None = None
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
        order_id = await _setup_test_order(theme, pages, work_type, model_name)
        
        full_tex, content_pages, total_pages = await _generate_test_content(
            order_id, model_name, theme, pages, work_type
        )
        
        if output_dir is None:
            output_dir = os.getcwd()
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        temp_dir = tempfile.mkdtemp()
        filename = f"test_work_{order_id}"
        
        output_tex_path, output_pdf_path, output_docx_path = await _compile_test_files(
            full_tex, output_dir, temp_dir, filename
        )
        
        await update_order_status(order_id, 'completed')
        
        _print_test_results(TestResultsParams(
            output_dir=output_dir,
            output_tex_path=output_tex_path,
            output_pdf_path=output_pdf_path,
            output_docx_path=output_docx_path,
            content_pages=content_pages,
            total_pages=total_pages,
            pages=pages
        ))
        
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
        if order_id:
            clear_conversation(order_id)
        
        if temp_dir and os.path.exists(temp_dir):
            try:
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
    if len(sys.argv) > ARG_INDEX_THEME:
        theme = sys.argv[ARG_INDEX_THEME]
    if len(sys.argv) > ARG_INDEX_PAGES:
        pages = int(sys.argv[ARG_INDEX_PAGES])
    if len(sys.argv) > ARG_INDEX_WORK_TYPE:
        work_type = sys.argv[ARG_INDEX_WORK_TYPE]
    if len(sys.argv) > ARG_INDEX_MODEL_NAME:
        model_name = sys.argv[ARG_INDEX_MODEL_NAME]
    
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

