# Scripts

Эта папка содержит вспомогательные скрипты для разработки и тестирования.

## Файлы

- `generate.py` - скрипт для генерации тестовых работ без запуска Telegram бота
- `remove_stuck_container.sh` - скрипт для удаления подвисших Docker контейнеров

## Использование

### generate.py

Генерация тестовой работы:

```bash
python scripts/generate.py [тема] [количество_страниц] [тип_работы] [модель]
```

Примеры:

```bash
# Генерация с параметрами по умолчанию
python scripts/generate.py

# Генерация с указанием темы и количества страниц
python scripts/generate.py "Искусственный интеллект" 10

# Полная команда
python scripts/generate.py "Тема работы" 15 "курсовая" "TEST"
```

Скрипт создаст файлы `.tex`, `.pdf` и `.docx` в текущей директории.

### remove_stuck_container.sh

Удаление подвисших Docker контейнеров, которые не удаляются стандартными командами:

```bash
./scripts/remove_stuck_container.sh <container_id>
```

Примеры:

```bash
# Удаление контейнера по ID
./scripts/remove_stuck_container.sh cfdfa9e9d9e6

# С правами sudo (если требуется)
sudo ./scripts/remove_stuck_container.sh cfdfa9e9d9e6
```

**Что делает скрипт:**
1. Получает PID процесса контейнера
2. Отключает автоперезапуск контейнера
3. Убивает процесс через `sudo kill -9`
4. Удаляет контейнер через `docker rm -f`
5. Проверяет результат удаления

**Когда использовать:**
- Когда `docker rm -f` возвращает ошибку `permission denied`
- Когда контейнер не останавливается стандартными командами
- Когда контейнер "завис" и не реагирует на команды

Подробнее см. [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)

