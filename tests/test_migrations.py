# tests/test_migrations.py
"""
Тесты для проверки миграций базы данных.
"""
import os
import tempfile
from unittest.mock import patch

import pytest

from db.migration_manager import get_current_version, get_migration_files, run_migrations


@pytest.mark.asyncio
async def test_migrations_can_be_applied():
    """Проверяет, что все миграции могут быть применены."""
    # Создаем временную БД
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    try:
        # Патчим DB_NAME для использования временной БД
        with patch('db.migration_manager.DB_NAME', temp_db_path):
            # Применяем миграции
            await run_migrations()
            
            # Проверяем, что миграции применились
            import aiosqlite
            
            async with aiosqlite.connect(temp_db_path) as db:
                version = await get_current_version(db)
                assert version > 0, "Миграции не были применены"
                
                # Проверяем, что таблица works создана
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='works'"
                )
                row = await cursor.fetchone()
                assert row is not None, "Таблица works не создана"
                
                # Проверяем, что таблица schema_version создана
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
                )
                row = await cursor.fetchone()
                assert row is not None, "Таблица schema_version не создана"
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


@pytest.mark.asyncio
async def test_migrations_are_idempotent():
    """Проверяет, что повторное применение миграций безопасно."""
    # Создаем временную БД
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    try:
        with patch('db.migration_manager.DB_NAME', temp_db_path):
            # Применяем миграции дважды
            await run_migrations()
            version_after_first = None
            
            import aiosqlite
            
            async with aiosqlite.connect(temp_db_path) as db:
                version_after_first = await get_current_version(db)
            
            await run_migrations()
            
            async with aiosqlite.connect(temp_db_path) as db:
                version_after_second = await get_current_version(db)
                assert version_after_first == version_after_second, "Версия изменилась при повторном применении"
    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


@pytest.mark.asyncio
async def test_migration_files_exist():
    """Проверяет, что файлы миграций существуют и имеют правильный формат."""
    migrations = await get_migration_files()
    assert len(migrations) > 0, "Миграции не найдены"
    
    # Проверяем, что миграции отсортированы по версии
    versions = [version for version, _ in migrations]
    assert versions == sorted(versions), "Миграции не отсортированы по версии"
    
    # Проверяем, что версии идут последовательно (1, 2, 3, ...)
    for i, version in enumerate(versions, start=1):
        assert version == i, f"Миграции должны быть последовательными, но найдена версия {version} вместо {i}"


@pytest.mark.asyncio
async def test_works_table_structure():
    """Проверяет, что таблица works имеет правильную структуру (без openai_thread_id)."""
    # Создаем временную БД
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    try:
        with patch('db.migration_manager.DB_NAME', temp_db_path):
            await run_migrations()
            
            import aiosqlite
            
            async with aiosqlite.connect(temp_db_path) as db:
                # Получаем структуру таблицы
                cursor = await db.execute("PRAGMA table_info(works)")
                columns = await cursor.fetchall()
                
                column_names = [col[1] for col in columns]
                
                # Проверяем наличие обязательных полей
                assert 'id' in column_names
                assert 'user_id' in column_names
                assert 'theme' in column_names
                assert 'pages' in column_names
                assert 'work_type' in column_names
                assert 'gpt_model' in column_names
                assert 'status' in column_names
                assert 'full_tex' in column_names
                assert 'created_at' in column_names
                
                # Проверяем, что openai_thread_id отсутствует
                assert 'openai_thread_id' not in column_names, "Поле openai_thread_id не должно присутствовать"
    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


@pytest.mark.asyncio
async def test_users_table_structure():
    """Проверяет, что таблица users имеет правильную структуру."""
    # Создаем временную БД
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    try:
        with patch('db.migration_manager.DB_NAME', temp_db_path):
            await run_migrations()
            
            import aiosqlite
            
            async with aiosqlite.connect(temp_db_path) as db:
                # Проверяем, что таблица users создана
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                )
                row = await cursor.fetchone()
                assert row is not None, "Таблица users не создана"
                
                # Получаем структуру таблицы
                cursor = await db.execute("PRAGMA table_info(users)")
                columns = await cursor.fetchall()
                
                column_names = [col[1] for col in columns]
                
                # Проверяем наличие обязательных полей
                assert 'user_id' in column_names, "Поле user_id должно присутствовать"
                assert 'created_at' in column_names, "Поле created_at должно присутствовать"
                
                # Проверяем, что user_id является PRIMARY KEY
                user_id_col = [col for col in columns if col[1] == 'user_id'][0]
                assert user_id_col[5] == 1, "user_id должен быть PRIMARY KEY"
    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


@pytest.mark.asyncio
async def test_works_foreign_key():
    """Проверяет, что в таблице works есть внешний ключ на users."""
    # Создаем временную БД
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    try:
        with patch('db.migration_manager.DB_NAME', temp_db_path):
            await run_migrations()
            
            import aiosqlite
            
            async with aiosqlite.connect(temp_db_path) as db:
                # Проверяем внешние ключи (SQLite хранит их в sqlite_master)
                cursor = await db.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='works'"
                )
                row = await cursor.fetchone()
                assert row is not None, "Таблица works не найдена"
                
                sql = row[0]
                # Проверяем наличие FOREIGN KEY в SQL
                assert 'FOREIGN KEY' in sql.upper() or 'REFERENCES users' in sql.upper(), \
                    "В таблице works должен быть внешний ключ на users"
    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)

