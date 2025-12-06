-- Миграция 002: Удаление поля openai_thread_id из таблицы works
-- Это поле больше не используется, так как проект ушел от OpenAI

-- SQLite не поддерживает ALTER TABLE DROP COLUMN напрямую
-- Используем стандартный подход: создаем новую таблицу, копируем данные, удаляем старую
-- Эта миграция безопасна: если поле уже отсутствует (база создана через миграцию 001),
-- то структура таблицы уже правильная, и мы просто пересоздадим её с той же структурой

-- Проверяем, существует ли поле openai_thread_id
-- Если таблица уже имеет правильную структуру (без openai_thread_id), 
-- то количество колонок будет 9, иначе 10
-- Но проще всего: всегда пересоздаем таблицу с правильной структурой

-- Создаем временную таблицу с новой структурой (без openai_thread_id)
CREATE TABLE works_new (
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

-- Копируем данные из старой таблицы
-- Если поле openai_thread_id существует, оно просто не будет скопировано
-- Если его нет, копируются все существующие поля
INSERT INTO works_new (id, user_id, theme, pages, work_type, gpt_model, status, full_tex, created_at)
SELECT id, user_id, theme, pages, work_type, gpt_model, status, full_tex, created_at
FROM works;

-- Удаляем старую таблицу
DROP TABLE works;

-- Переименовываем новую таблицу
ALTER TABLE works_new RENAME TO works;

