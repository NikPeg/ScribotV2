# Deployment

Эта папка содержит файлы для развертывания приложения с помощью Docker.

## Файлы

- `Dockerfile` - образ Docker для приложения
- `docker-compose.yml` - конфигурация Docker Compose для запуска приложения

## Использование

Для запуска приложения с помощью Docker Compose:

```bash
cd deployment
docker-compose up -d
```

Или из корневой директории проекта:

```bash
docker-compose -f deployment/docker-compose.yml up -d
```

## Примечания

- Docker Compose должен запускаться из корневой директории проекта или из папки `deployment`
- Файл `.env` должен находиться в корневой директории проекта
- Директории `data/` и `logs/` должны находиться в корневой директории проекта

## CI/CD и GitHub Actions

Для настройки автоматического деплоя через GitHub Actions см. [SECRETS.md](./SECRETS.md)

**Важно:** При настройке SSH ключей убедитесь, что публичный ключ добавлен для пользователя, указанного в секрете `YC_INSTANCE_USER` (обычно `ubuntu`). Подробности в разделе "⚠️ КРИТИЧЕСКИ ВАЖНО: Проблема с пользователями и authorized_keys" в [SECRETS.md](./SECRETS.md).

