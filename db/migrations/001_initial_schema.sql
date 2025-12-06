-- Миграция 001: Начальная схема базы данных
-- Создает таблицы users и works без поля openai_thread_id

-- Создаем таблицу пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    created_at TIMESTAMP NOT NULL
);

-- Создаем таблицу работ с внешним ключом на users
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    theme TEXT NOT NULL,
    pages INTEGER NOT NULL,
    work_type TEXT NOT NULL,
    gpt_model TEXT NOT NULL,
    status TEXT NOT NULL,
    full_tex TEXT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

