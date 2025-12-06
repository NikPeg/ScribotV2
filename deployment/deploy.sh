#!/bin/bash
# Скрипт деплоя ScribotV2
# Используется CI/CD пайплайном

set -e  # Остановка при ошибке

echo "🔄 Начинаем деплой..."

# Проверяем что все переменные окружения установлены
REQUIRED_VARS="BOT_TOKEN CHANNEL_URL FEEDBACK_URL SOS_URL ADMIN_ID LLM_TOKEN YC_REGISTRY_ID NEW_IMAGE YC_SA_JSON_CREDENTIALS"
for VAR in $REQUIRED_VARS; do
  if [ -z "${!VAR}" ]; then
    echo "❌ Ошибка: переменная $VAR не установлена"
    exit 1
  fi
done

# Создаем директории если их нет
export DEPLOY_DIR="$HOME/ScribotV2"
export DEPLOYMENT_DIR="$DEPLOY_DIR/deployment"
mkdir -p "$DEPLOY_DIR/data" "$DEPLOY_DIR/logs" "$DEPLOYMENT_DIR"
echo "📁 Директория деплоя: $DEPLOY_DIR"

# Проверяем наличие docker-compose.prod.yml
if [ ! -f "$DEPLOYMENT_DIR/docker-compose.prod.yml" ]; then
  echo "❌ Ошибка: docker-compose.prod.yml не найден!"
  ls -la "$DEPLOYMENT_DIR" || true
  exit 1
fi
echo "✅ Файл docker-compose.prod.yml найден"

# Логинимся в Yandex Container Registry
echo "🔐 Логинимся в Yandex Container Registry..."
echo "$YC_SA_JSON_CREDENTIALS" > /tmp/key.json
cat /tmp/key.json | sudo docker login --username json_key --password-stdin cr.yandex/$YC_REGISTRY_ID
rm /tmp/key.json

# Сохраняем информацию о текущем работающем контейнере
CURRENT_IMAGE=""
if sudo docker ps --filter name=scribot_bot --format "{{.Image}}" | grep -q .; then
  CURRENT_IMAGE=$(sudo docker ps --filter name=scribot_bot --format "{{.Image}}")
  echo "📸 Текущий образ: $CURRENT_IMAGE"
  sudo docker tag "$CURRENT_IMAGE" "$BACKUP_IMAGE" 2>/dev/null || echo "⚠️ Не удалось создать backup тег"
else
  echo "⚠️ Текущий контейнер не найден"
fi

# Скачиваем новый образ
echo "⬇️ Скачиваем новый образ: $NEW_IMAGE"
sudo docker pull "$NEW_IMAGE"

# ============================================================
# ОСТАНОВКА КОНТЕЙНЕРА
# ============================================================
echo ""
echo "⏸️ Останавливаем текущий контейнер..."

# Пробуем через docker-compose
cd "$DEPLOYMENT_DIR"
echo "🛑 Пробуем docker-compose down..."
sudo docker-compose -f docker-compose.prod.yml down --remove-orphans --timeout 30 2>&1 || true
sleep 3

# Получаем ID контейнеров
CONTAINER_IDS=$(sudo docker ps -a --filter name=scribot_bot --format "{{.ID}}" || true)

if [ -n "$CONTAINER_IDS" ]; then
  echo "🗑️ Найдены контейнеры: $CONTAINER_IDS"
  
  for CONTAINER_ID in $CONTAINER_IDS; do
    echo ""
    echo "========== Обработка $CONTAINER_ID =========="
    
    # [1] Отключаем автоперезапуск
    echo "[1/4] docker update --restart=no"
    sudo docker update --restart=no "$CONTAINER_ID" 2>&1 || true
    
    # [2] docker stop
    echo "[2/4] docker stop --timeout 10"
    sudo docker stop --timeout 10 "$CONTAINER_ID" 2>&1 || true
    sleep 2
    
    # [3] docker kill если нужно
    CONTAINER_STATUS=$(sudo docker inspect "$CONTAINER_ID" --format '{{.State.Status}}' 2>/dev/null || echo "unknown")
    echo "      Статус: $CONTAINER_STATUS"
    if [ "$CONTAINER_STATUS" = "running" ]; then
      echo "[3/4] docker kill"
      sudo docker kill "$CONTAINER_ID" 2>&1 || true
      sleep 2
    fi
    
    # [4] docker rm -f
    echo "[4/4] docker rm -f"
    sudo docker rm -f "$CONTAINER_ID" 2>&1 || true
    sleep 1
  done
fi

# Проверяем, удалился ли контейнер
if sudo docker ps -a --filter name=scribot_bot --format "{{.Names}}" | grep -q scribot_bot; then
  echo ""
  echo "⚠️ ========== ЭКСТРЕННЫЕ МЕРЫ =========="
  
  REMAINING_IDS=$(sudo docker ps -a --filter name=scribot_bot --format "{{.ID}}")
  for CONTAINER_ID in $REMAINING_IDS; do
    echo "🔧 Экстренная обработка $CONTAINER_ID..."
    
    # Получаем PID и убиваем напрямую
    CONTAINER_PID=$(sudo docker inspect "$CONTAINER_ID" --format '{{.State.Pid}}' 2>/dev/null || echo "0")
    
    if [ "$CONTAINER_PID" != "0" ] && [ -n "$CONTAINER_PID" ]; then
      echo "💀 Убиваем процесс $CONTAINER_PID через kill -9..."
      sudo kill -9 "$CONTAINER_PID" 2>&1 || true
      sleep 3
      
      # Проверяем
      if ps -p "$CONTAINER_PID" > /dev/null 2>&1; then
        echo "⚠️ Процесс $CONTAINER_PID всё ещё жив!"
      else
        echo "✅ Процесс $CONTAINER_PID убит"
      fi
    fi
    
    # Пробуем удалить
    echo "🗑️ docker rm -f $CONTAINER_ID"
    sudo docker rm -f "$CONTAINER_ID" 2>&1 || true
    sleep 1
  done
fi

# Ещё раз проверяем
if sudo docker ps -a --filter name=scribot_bot --format "{{.Names}}" | grep -q scribot_bot; then
  echo ""
  echo "🔄 Перезапускаем Docker daemon..."
  sudo systemctl restart docker 2>&1 || sudo service docker restart 2>&1 || true
  sleep 10
  
  # Повторный логин
  echo "🔐 Повторный логин в registry..."
  echo "$YC_SA_JSON_CREDENTIALS" > /tmp/key.json
  cat /tmp/key.json | sudo docker login --username json_key --password-stdin cr.yandex/$YC_REGISTRY_ID || true
  rm -f /tmp/key.json
  
  # Финальная попытка удаления
  FINAL_IDS=$(sudo docker ps -a --filter name=scribot_bot --format "{{.ID}}")
  for FINAL_ID in $FINAL_IDS; do
    sudo docker rm -f "$FINAL_ID" 2>&1 || true
  done
  sleep 2
  
  if sudo docker ps -a --filter name=scribot_bot --format "{{.Names}}" | grep -q scribot_bot; then
    echo "❌ НЕВОЗМОЖНО УДАЛИТЬ КОНТЕЙНЕР!"
    sudo docker ps -a --filter name=scribot_bot
    exit 1
  fi
fi

echo "✅ Все старые контейнеры удалены"

# ============================================================
# ЗАПУСК НОВОГО КОНТЕЙНЕРА
# ============================================================
echo ""
echo "🚀 Запускаем новый контейнер..."

# Создаем .env файл
echo "📝 Создаем .env файл..."
cat > "$DEPLOYMENT_DIR/.env" << EOF
BOT_TOKEN=$BOT_TOKEN
CHANNEL_URL=$CHANNEL_URL
FEEDBACK_URL=$FEEDBACK_URL
SOS_URL=$SOS_URL
ADMIN_ID=$ADMIN_ID
LOG_LEVEL=${LOG_LEVEL:-all}
REQUIRED_CHANNELS=${REQUIRED_CHANNELS:-}
BASE_PRICE=${BASE_PRICE:-100}
PROMOTION_TEXT=${PROMOTION_TEXT:-}
LLM_TOKEN=$LLM_TOKEN
YC_REGISTRY_ID=$YC_REGISTRY_ID
NEW_IMAGE=$NEW_IMAGE
EOF

# Запускаем
cd "$DEPLOYMENT_DIR"
echo "📦 Образ: $NEW_IMAGE"
sudo docker-compose -f docker-compose.prod.yml up -d

# Ждем healthcheck
echo "⏳ Ожидаем healthcheck (до 60 секунд)..."
TIMEOUT=60
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
  HEALTH=$(sudo docker inspect --format='{{.State.Health.Status}}' scribot_bot 2>/dev/null || echo "none")
  
  if [ "$HEALTH" = "healthy" ]; then
    echo "✅ Контейнер healthy!"
    break
  elif [ "$HEALTH" = "none" ]; then
    if sudo docker ps --filter name=scribot_bot --filter status=running | grep -q scribot_bot; then
      echo "ℹ️ Контейнер работает (без healthcheck)"
      break
    fi
  fi
  
  echo "⏳ Статус: $HEALTH (${ELAPSED}s)"
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

# Проверяем результат
if sudo docker ps --filter name=scribot_bot --filter status=running | grep -q scribot_bot; then
  echo ""
  echo "✅ Деплой успешен!"
  echo "📊 Статус контейнера:"
  sudo docker ps --filter name=scribot_bot
  echo ""
  echo "📝 Последние логи:"
  sudo docker logs scribot_bot --tail=20
else
  echo "❌ Контейнер не работает!"
  sudo docker logs scribot_bot --tail=50 2>&1 || true
  
  # Откат
  if [ -n "$CURRENT_IMAGE" ] && [ -n "$BACKUP_IMAGE" ]; then
    echo "🔙 Откатываемся к $BACKUP_IMAGE..."
    sudo docker rm -f scribot_bot 2>/dev/null || true
    sudo docker tag "$BACKUP_IMAGE" "$NEW_IMAGE" || true
    sudo docker-compose -f docker-compose.prod.yml up -d
    sleep 10
    sudo docker logs scribot_bot --tail=20
  fi
  exit 1
fi

