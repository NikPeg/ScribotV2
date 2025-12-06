# db/migration_manager.py
"""
Менеджер миграций базы данных.
Применяет миграции из папки migrations/ в порядке их версий.
"""
import os
import logging
from pathlib import Path
from typing import List, Tuple

import aiosqlite

logger = logging.getLogger(__name__)

# Путь к базе данных
DB_DIR = os.getenv('DB_DIR', '.')
DB_NAME = os.path.join(DB_DIR, 'scribot.db')

# Путь к папке с миграциями
MIGRATIONS_DIR = Path(__file__).parent / 'migrations'


async def get_current_version(db: aiosqlite.Connection) -> int:
    """Получает текущую версию схемы базы данных."""
    try:
        cursor = await db.execute('SELECT version FROM schema_version ORDER BY version DESC LIMIT 1')
        row = await cursor.fetchone()
        return row[0] if row else 0
    except aiosqlite.OperationalError:
        # Таблица schema_version не существует - база еще не инициализирована
        return 0


async def set_version(db: aiosqlite.Connection, version: int):
    """Устанавливает версию схемы базы данных."""
    await db.execute('INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, datetime("now"))', (version,))
    await db.commit()


async def get_migration_files() -> List[Tuple[int, Path]]:
    """Получает список файлов миграций, отсортированных по версии."""
    migrations = []
    
    if not MIGRATIONS_DIR.exists():
        logger.warning(f"Папка миграций {MIGRATIONS_DIR} не найдена")
        return migrations
    
    for file_path in sorted(MIGRATIONS_DIR.glob('*.sql')):
        # Извлекаем номер версии из имени файла (например, 001_initial.sql -> 1)
        filename = file_path.stem
        try:
            version = int(filename.split('_')[0])
            migrations.append((version, file_path))
        except (ValueError, IndexError):
            logger.warning(f"Неверный формат имени файла миграции: {file_path.name}")
    
    return migrations


async def apply_migration(db: aiosqlite.Connection, version: int, file_path: Path):
    """Применяет одну миграцию из файла."""
    logger.info(f"Применяем миграцию {version} из {file_path.name}")
    
    try:
        # Читаем SQL из файла
        sql = file_path.read_text(encoding='utf-8')
        
        # SQLite не поддерживает выполнение нескольких команд через execute()
        # Разбиваем по ';' и выполняем каждую команду отдельно
        commands = [cmd.strip() for cmd in sql.split(';') if cmd.strip()]
        
        for command in commands:
            if command:
                await db.execute(command)
        
        await db.commit()
        
        # Обновляем версию схемы
        await set_version(db, version)
        logger.info(f"Миграция {version} успешно применена")
        
    except Exception as e:
        logger.error(f"Ошибка при применении миграции {version}: {e}")
        await db.rollback()
        raise


async def init_schema_version_table(db: aiosqlite.Connection):
    """Создает таблицу для хранения версии схемы, если её нет."""
    await db.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    ''')
    await db.commit()


async def run_migrations():
    """Применяет все непримененные миграции."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу версий, если её нет
        await init_schema_version_table(db)
        
        # Получаем текущую версию
        current_version = await get_current_version(db)
        logger.info(f"Текущая версия схемы: {current_version}")
        
        # Получаем список миграций
        migrations = await get_migration_files()
        
        if not migrations:
            logger.warning("Миграции не найдены")
            return
        
        # Применяем миграции, которые еще не применены
        applied_count = 0
        for version, file_path in migrations:
            if version > current_version:
                await apply_migration(db, version, file_path)
                applied_count += 1
        
        if applied_count > 0:
            logger.info(f"Применено миграций: {applied_count}")
        else:
            logger.info("Все миграции уже применены")

