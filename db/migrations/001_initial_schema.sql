-- Миграция 001: Начальная схема базы данных
-- Создает таблицу works без поля openai_thread_id

CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    theme TEXT NOT NULL,
    pages INTEGER NOT NULL,
    work_type TEXT NOT NULL,
    gpt_model TEXT NOT NULL,
    status TEXT NOT NULL,
    full_tex TEXT,
    created_at TIMESTAMP NOT NULL
);

