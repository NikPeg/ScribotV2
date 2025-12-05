# Настройка секретов для GitHub Actions

Для работы CD pipeline необходимо настроить следующие секреты в GitHub репозитории:

**Settings → Secrets and variables → Actions → New repository secret**

## Секреты для Yandex Cloud

### 1. `YC_SA_JSON_CREDENTIALS`
JSON ключ сервисного аккаунта для доступа к Yandex Container Registry.

**Как получить:**
1. Перейдите в Yandex Cloud Console → IAM → Service accounts
2. Создайте или выберите сервисный аккаунт
3. Назначьте роль `container-registry.images.pusher` и `container-registry.images.puller`
4. Создайте JSON ключ: Service account → Keys → Create key → JSON
5. Скопируйте весь JSON и добавьте как секрет

### 2. `YC_REGISTRY_ID`
ID реестра контейнеров в Yandex Cloud.

**Как получить:**
1. Перейдите в Yandex Cloud Console → Container Registry
2. Выберите или создайте реестр
3. Скопируйте ID реестра (обычно формат: `crpXXXXXXXXXXXXX`)

### 3. `YC_INSTANCE_IP`
IP адрес виртуальной машины в Yandex Cloud, куда будет происходить деплой.

**Как получить:**
1. Перейдите в Yandex Cloud Console → Compute Cloud → Virtual machines
2. Выберите вашу VM
3. Скопируйте публичный IP адрес

### 4. `YC_INSTANCE_USER`
Имя пользователя для SSH подключения к виртуальной машине.

**Обычно:** `ubuntu`, `yandex` или `admin` (зависит от образа)

### 5. `SSH_PRIVATE_KEY`
Приватный SSH ключ для подключения к виртуальной машине.

**Как получить:**
1. Если используете существующий ключ - скопируйте приватную часть
2. Если создаете новый:
   ```bash
   ssh-keygen -t rsa -b 4096 -C "github-actions"
   ```
3. Добавьте публичный ключ на VM:
   ```bash
   ssh-copy-id -i ~/.ssh/id_rsa.pub user@your-vm-ip
   ```
4. Скопируйте приватный ключ (содержимое `~/.ssh/id_rsa`) и добавьте как секрет

## Секреты приложения

### 6. `BOT_TOKEN`
Токен Telegram бота от [@BotFather](https://t.me/BotFather)

### 7. `CHAT_URL`
URL чата для отправки сообщений

### 8. `FEEDBACK_URL`
URL для отправки обратной связи

### 9. `SOS_URL`
URL для SOS запросов

### 10. `ADMIN_ID`
Telegram ID администратора (число)

### 11. `LLM_TOKEN`
Токен для доступа к LLM API (OpenAI, Yandex GPT и т.д.)

### 12. `LOG_LEVEL` (опционально)
Уровень логирования. По умолчанию: `all`
Возможные значения: `all`, `none`

### 13. `REQUIRED_CHANNELS` (опционально)
Список обязательных каналов для подписки, разделенных запятыми.
Формат: `@channel1,@channel2` или `channel_id1,channel_id2`
По умолчанию: пустая строка

## Проверка настройки

После добавления всех секретов:
1. Убедитесь, что все секреты добавлены в репозиторий
2. Сделайте push в ветку `main`
3. Проверьте выполнение workflow в разделе Actions
4. При успешном деплое бот должен запуститься на сервере

## Структура директорий на сервере

После первого деплоя на сервере будет создана следующая структура:

```
~/scribot-bot/
├── docker-compose.prod.yml  # Конфигурация для продакшена
├── .env                     # Переменные окружения
├── data/                    # База данных (монтируется с хоста)
│   └── scribot.db
└── logs/                    # Логи приложения (монтируются с хоста)
    └── llm_*.log
```

**Важно:** База данных и логи находятся на хосте, а не в контейнере, что позволяет:
- Подключаться к базе данных без входа в контейнер
- Просматривать логи напрямую на сервере
- Сохранять данные при пересоздании контейнера

