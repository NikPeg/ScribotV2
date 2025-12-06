# db/database.py
import os
from datetime import datetime

import aiosqlite

from db.migration_manager import run_migrations

# Путь к базе данных: используем переменную окружения или дефолтный путь
DB_DIR = os.getenv('DB_DIR', '.')
DB_NAME = os.path.join(DB_DIR, 'scribot.db')

async def init_db():
    """Инициализирует базу данных и применяет миграции."""
    # Применяем миграции (они создадут таблицы при необходимости)
    await run_migrations()

async def create_order(user_id: int, theme: str, pages: int, work_type: str, gpt_model: str) -> int:
    """Создает новый заказ в БД и возвращает его ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            '''
            INSERT INTO works (user_id, theme, pages, work_type, gpt_model, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (user_id, theme, pages, work_type, gpt_model, 'created', datetime.now())
        )
        await db.commit()
        return cursor.lastrowid

async def update_order_status(order_id: int, status: str):
    """Обновляет статус заказа."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE works SET status = ? WHERE id = ?', (status, order_id))
        await db.commit()

async def save_full_tex(order_id: int, tex_content: str):
    """Сохраняет полный tex-файл работы в БД."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE works SET full_tex = ? WHERE id = ?', (tex_content, order_id))
        await db.commit()

async def get_order_info(order_id: int):
    """Получает информацию о заказе по ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT user_id, theme, pages, work_type, gpt_model, full_tex FROM works WHERE id = ?',
            (order_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'theme': row[1],
                'pages': row[2],
                'work_type': row[3],
                'gpt_model': row[4],
                'full_tex': row[5]
            }
        return None
