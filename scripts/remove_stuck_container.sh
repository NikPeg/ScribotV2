#!/bin/bash
# Скрипт для удаления подвисших Docker контейнеров
# Использование: ./remove_stuck_container.sh [container_id|container_name]
# Если ID/имя не указано, ищет контейнер scribot_bot

CONTAINER_ID=$1

# Если ID не указан, ищем scribot_bot
if [ -z "$CONTAINER_ID" ]; then
    echo "🔍 ID контейнера не указан, ищем scribot_bot..."
    CONTAINER_ID=$(sudo docker ps -a --filter name=scribot_bot --format "{{.ID}}" | head -1)
    
    if [ -z "$CONTAINER_ID" ]; then
        echo "❌ Контейнер scribot_bot не найден"
        echo ""
        echo "Использование: $0 [container_id]"
        echo "Пример: $0 786b87116b67"
        exit 1
    fi
    echo "📦 Найден контейнер: $CONTAINER_ID"
fi

echo "=========================================="
echo "🔧 Удаление зависшего контейнера: $CONTAINER_ID"
echo "=========================================="

# Показываем информацию о контейнере
echo ""
echo "📊 Информация о контейнере:"
sudo docker ps -a --filter id=$CONTAINER_ID --format "ID: {{.ID}}\nName: {{.Names}}\nImage: {{.Image}}\nStatus: {{.Status}}" 2>/dev/null || echo "Контейнер не найден"
echo ""

# Шаг 1: Отключаем автоперезапуск
echo "🛑 Шаг 1: Отключаем автоперезапуск..."
sudo docker update --restart=no $CONTAINER_ID 2>/dev/null || true

# Шаг 2: Пытаемся остановить через docker stop
echo "⏹️  Шаг 2: Пытаемся docker stop (timeout 10s)..."
sudo docker stop --timeout 10 $CONTAINER_ID 2>/dev/null || true
sleep 2

# Проверяем статус
CONTAINER_STATUS=$(sudo docker inspect $CONTAINER_ID --format '{{.State.Status}}' 2>/dev/null || echo "removed")
if [ "$CONTAINER_STATUS" = "removed" ] || [ "$CONTAINER_STATUS" = "exited" ]; then
    echo "✅ Контейнер остановлен через docker stop"
else
    # Шаг 3: Используем docker kill
    echo "🔪 Шаг 3: docker stop не помог, используем docker kill..."
    sudo docker kill $CONTAINER_ID 2>/dev/null || true
    sleep 2
fi

# Шаг 4: Удаляем контейнер
echo "🗑️  Шаг 4: Удаляем контейнер..."
sudo docker rm -f $CONTAINER_ID 2>/dev/null || true
sleep 1

# Проверяем, удален ли контейнер
if sudo docker ps -a --format "{{.ID}}" | grep -q "^${CONTAINER_ID:0:12}"; then
    echo ""
    echo "⚠️  Контейнер всё ещё существует. Применяем экстренные меры..."
    
    # Шаг 5: Получаем PID и убиваем процесс напрямую
    echo "🔍 Шаг 5: Получаем PID контейнера..."
    CONTAINER_PID=$(sudo docker inspect $CONTAINER_ID --format '{{.State.Pid}}' 2>/dev/null || echo "0")
    
    if [ "$CONTAINER_PID" != "0" ] && [ -n "$CONTAINER_PID" ]; then
        echo "📌 PID контейнера: $CONTAINER_PID"
        
        # Убиваем процесс
        echo "💀 Убиваем процесс $CONTAINER_PID через kill -9..."
        sudo kill -9 $CONTAINER_PID 2>/dev/null || true
        sleep 3
        
        # Пытаемся удалить ещё раз
        echo "🗑️  Повторная попытка удаления..."
        sudo docker rm -f $CONTAINER_ID 2>/dev/null || true
        sleep 1
    fi
    
    # Финальная проверка
    if sudo docker ps -a --format "{{.ID}}" | grep -q "^${CONTAINER_ID:0:12}"; then
        echo ""
        echo "❌ КРИТИЧЕСКАЯ ОШИБКА: Контейнер-зомби не удаётся удалить!"
        echo ""
        echo "Попробуйте следующее:"
        echo "  1. Перезапустить Docker daemon:"
        echo "     sudo systemctl restart docker"
        echo ""
        echo "  2. Или перезагрузить сервер:"
        echo "     sudo reboot"
        echo ""
        exit 1
    fi
fi

echo ""
echo "✅ Контейнер успешно удалён!"
echo ""

# Очищаем неиспользуемые ресурсы
echo "🧹 Очищаем неиспользуемые Docker ресурсы..."
sudo docker system prune -f 2>/dev/null || true

echo ""
echo "✅ Готово! Можно запускать новый контейнер."

