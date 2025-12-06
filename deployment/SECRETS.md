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
   ssh-keygen -t ed25519 -C "github-actions"
   # или для RSA:
   ssh-keygen -t rsa -b 4096 -C "github-actions"
   ```
3. Добавьте публичный ключ на VM:
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519.pub user@your-vm-ip
   ```
4. Скопируйте приватный ключ (содержимое `~/.ssh/id_ed25519` или `~/.ssh/id_rsa`) и добавьте как секрет

**⚠️ КРИТИЧЕСКИ ВАЖНО: Проблема с пользователями и authorized_keys**

GitHub Actions подключается к серверу как пользователь, указанный в секрете `YC_INSTANCE_USER` (обычно `ubuntu`). 
**Публичный ключ должен быть добавлен именно для этого пользователя!**

**Частая ошибка:**
- Публичный ключ добавлен для другого пользователя (например, `nikpeganov`)
- GitHub Actions пытается подключиться как `ubuntu`
- Результат: `ssh: unable to authenticate, attempted methods [none publickey]`

**Правильная настройка:**

1. Убедитесь, что пользователь из `YC_INSTANCE_USER` существует на сервере:
   ```bash
   yc compute ssh --id <instance-id> "sudo id ubuntu"
   ```

2. Проверьте, что у этого пользователя есть файл `authorized_keys`:
   ```bash
   yc compute ssh --id <instance-id> "sudo ls -la /home/ubuntu/.ssh/authorized_keys"
   ```

3. Добавьте публичный ключ для правильного пользователя:
   ```bash
   # Извлеките публичный ключ из приватного:
   ssh-keygen -y -f ~/.ssh/id_ed25519 > /tmp/public_key.pub
   
   # Добавьте его на сервер для пользователя ubuntu:
   yc compute ssh --id <instance-id> "echo '$(cat /tmp/public_key.pub)' | sudo tee -a /home/ubuntu/.ssh/authorized_keys"
   
   # Установите правильные права:
   yc compute ssh --id <instance-id> "sudo chmod 600 /home/ubuntu/.ssh/authorized_keys && sudo chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys"
   ```

4. Проверьте подключение:
   ```bash
   ssh -i ~/.ssh/id_ed25519 ubuntu@<vm-ip> "echo 'Connection successful!'"
   ```

**Формат ключа в GitHub Secrets:**

При добавлении приватного ключа в GitHub Secrets убедитесь, что:
- Ключ начинается с `-----BEGIN OPENSSH PRIVATE KEY-----` или `-----BEGIN RSA PRIVATE KEY-----`
- Ключ заканчивается на `-----END OPENSSH PRIVATE KEY-----` или `-----END RSA PRIVATE KEY-----`
- Все строки между BEGIN и END включены (ключ не обрезан)
- Переносы строк сохранены
- Нет лишних пробелов в начале/конце

**Пример правильного формата:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFh
YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFh
...
-----END OPENSSH PRIVATE KEY-----
```

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

### 14. `BASE_PRICE` (опционально)
Базовая цена в звездочках Telegram за работу.
По умолчанию: `100`

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

## Troubleshooting

### Ошибка SSH аутентификации

**Симптомы:**
```
ssh: handshake failed: ssh: unable to authenticate, attempted methods [none publickey], no supported methods remain
```

**Причины и решения:**

1. **Публичный ключ не добавлен для пользователя из `YC_INSTANCE_USER`**
   - Проверьте, что публичный ключ добавлен именно для того пользователя, который указан в секрете `YC_INSTANCE_USER`
   - См. раздел выше "⚠️ КРИТИЧЕСКИ ВАЖНО: Проблема с пользователями и authorized_keys"

2. **Неправильный формат ключа в GitHub Secrets**
   - Убедитесь, что ключ полный (не обрезан)
   - Проверьте, что все строки между BEGIN и END включены
   - Убедитесь, что переносы строк сохранены

3. **Неправильные права доступа на сервере**
   - Файл `authorized_keys` должен иметь права `600`
   - Директория `.ssh` должна иметь права `700`
   - Владелец файлов должен быть правильный пользователь

4. **Проверка подключения вручную:**
   ```bash
   # Извлеките публичный ключ из приватного
   ssh-keygen -y -f <path-to-private-key> > public_key.pub
   
   # Попробуйте подключиться
   ssh -i <path-to-private-key> <user>@<vm-ip> "echo 'Success'"
   ```

### Ошибка прав доступа к Docker

**Симптомы:**
```
permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
```

**Причины и решения:**

1. **Пользователь не в группе `docker`**
   - Добавьте пользователя в группу docker:
     ```bash
     yc compute ssh --id <instance-id> "sudo usermod -aG docker ubuntu"
     ```
   - **Важно:** Изменения в группах применяются только после перелогина. В GitHub Actions используется `sudo docker` для обхода этой проблемы.

2. **Настройка sudo без пароля для docker команд**
   - Для работы GitHub Actions необходимо настроить sudo без пароля для команд docker:
     ```bash
     yc compute ssh --id <instance-id> "echo 'ubuntu ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose' | sudo tee /etc/sudoers.d/docker-ubuntu"
     ```
   - Это позволяет пользователю `ubuntu` выполнять команды docker через sudo без ввода пароля.

3. **Проверка прав на Docker socket**
   - Убедитесь, что `/var/run/docker.sock` имеет правильные права:
     ```bash
     yc compute ssh --id <instance-id> "ls -la /var/run/docker.sock"
     ```
   - Должно быть: `srw-rw---- 1 root docker`

4. **Проверка работы docker через sudo**
   ```bash
   yc compute ssh --id <instance-id> "sudo -u ubuntu sudo -n docker ps"
   ```
   - Команда должна выполниться без ошибок

**Примечание:** В workflow файле все команды `docker` используют `sudo docker`, что гарантирует работу даже если пользователь не перелогинился после добавления в группу docker.

### Проверка логов GitHub Actions

Если деплой не работает:
1. Перейдите в GitHub → Actions → выберите последний workflow
2. Проверьте логи шага "Copy docker-compose.prod.yml to server"
3. Проверьте логи шага "Deploy to server via SSH"
4. Ошибки обычно указывают на конкретную проблему

