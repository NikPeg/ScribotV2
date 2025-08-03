# db/database.py
import aiosqlite
from datetime import datetime

DB_NAME = 'scribot.db'

async def init_db():
    """Инициализирует базу данных и создает таблицу, если её нет."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                theme TEXT NOT NULL,
                pages INTEGER NOT NULL,
                work_type TEXT NOT NULL,
                gpt_model TEXT NOT NULL,
                openai_thread_id TEXT,
                status TEXT NOT NULL,
                full_tex TEXT,
                created_at TIMESTAMP NOT NULL
            )
        ''')
        await db.commit()

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

async def update_order_thread_id(order_id: int, thread_id: str):
    """Сохраняет ID потока OpenAI для заказа."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE works SET openai_thread_id = ? WHERE id = ?', (thread_id, order_id))
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
