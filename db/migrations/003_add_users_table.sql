-- Миграция 003: Добавление таблицы users и связи с works
-- Создает таблицу пользователей и добавляет внешний ключ в works

-- Создаем таблицу users
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    created_at TIMESTAMP NOT NULL
);

-- Добавляем внешний ключ в works (если его еще нет)
-- SQLite не поддерживает ADD CONSTRAINT напрямую, поэтому нужно пересоздать таблицу
-- Но сначала проверим, существует ли уже внешний ключ через пересоздание таблицы

-- Создаем временную таблицу works с внешним ключом
CREATE TABLE works_new (
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

-- Копируем данные из старой таблицы
INSERT INTO works_new (id, user_id, theme, pages, work_type, gpt_model, status, full_tex, created_at)
SELECT id, user_id, theme, pages, work_type, gpt_model, status, full_tex, created_at
FROM works;

-- Удаляем старую таблицу
DROP TABLE works;

-- Переименовываем новую таблицу
ALTER TABLE works_new RENAME TO works;

