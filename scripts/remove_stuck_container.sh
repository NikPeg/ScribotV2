#!/bin/bash
# Скрипт для удаления подвисших Docker контейнеров
# Использование: ./remove_stuck_container.sh <container_id>

set -e

CONTAINER_ID=$1

if [ -z "$CONTAINER_ID" ]; then
    echo "❌ Ошибка: не указан ID контейнера"
    echo "Использование: $0 <container_id>"
    echo ""
    echo "Пример:"
    echo "  $0 cfdfa9e9d9e6"
    exit 1
fi

echo "🔍 Получаем PID контейнера $CONTAINER_ID..."
CONTAINER_PID=$(sudo docker inspect $CONTAINER_ID --format '{{.State.Pid}}' 2>/dev/null || echo "")

if [ -z "$CONTAINER_PID" ] || [ "$CONTAINER_PID" = "0" ]; then
    echo "❌ Не удалось получить PID контейнера"
    echo "Проверьте, что контейнер существует:"
    echo "  sudo docker ps -a | grep $CONTAINER_ID"
    exit 1
fi

echo "📌 PID контейнера: $CONTAINER_PID"

echo "🛑 Отключаем автоперезапуск..."
sudo docker update --restart=no $CONTAINER_ID 2>/dev/null || true

echo "🔪 Убиваем процесс контейнера..."
sudo kill -9 $CONTAINER_PID 2>/dev/null || true

echo "⏳ Ждем 2 секунды..."
sleep 2

echo "🗑️  Удаляем контейнер..."
sudo docker rm -f $CONTAINER_ID 2>/dev/null || true

echo "✅ Проверяем результат..."
if sudo docker ps -a --format "{{.ID}}" | grep -q "^$CONTAINER_ID$"; then
    echo "❌ Контейнер все еще существует"
    echo ""
    echo "Попробуйте выполнить вручную:"
    echo "  sudo kill -9 $CONTAINER_PID"
    echo "  sudo docker rm -f $CONTAINER_ID"
    exit 1
else
    echo "✅ Контейнер успешно удален"
fi

