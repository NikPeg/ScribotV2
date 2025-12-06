# Troubleshooting Guide

## Удаление подвисших контейнеров Docker

Иногда контейнеры Docker могут "зависнуть" и не удаляться стандартными командами. Это может происходить из-за проблем с правами доступа или процессов, которые не могут быть остановлены обычными способами.

### Симптомы

- Команда `docker rm -f <container_id>` возвращает ошибку: `could not kill container: permission denied`
- Контейнер продолжает работать, несмотря на попытки его остановить
- Стандартные команды `docker stop` и `docker kill` не работают

### Решение

#### Шаг 1: Получите PID процесса контейнера

```bash
CONTAINER_ID="cfdfa9e9d9e6"  # Замените на ID вашего контейнера
CONTAINER_PID=$(sudo docker inspect $CONTAINER_ID --format '{{.State.Pid}}' 2>/dev/null)
echo "PID контейнера: $CONTAINER_PID"
```

#### Шаг 2: Убейте процесс контейнера напрямую

```bash
sudo kill -9 $CONTAINER_PID
```

**Важно:** Используйте `sudo kill -9`, так как обычный `kill` может не иметь достаточных прав.

#### Шаг 3: Подождите и удалите контейнер

```bash
sleep 2
sudo docker rm -f $CONTAINER_ID
```

#### Шаг 4: Проверьте результат

```bash
sudo docker ps -a | grep <container_name>
```

Если контейнер исчез из списка - проблема решена.

### Автоматизированное решение

Для автоматизации процесса удаления подвисших контейнеров используйте готовый скрипт:

```bash
./scripts/remove_stuck_container.sh <container_id>
```

**Пример использования:**
```bash
./scripts/remove_stuck_container.sh cfdfa9e9d9e6
```

Скрипт автоматически:
1. Получает PID процесса контейнера
2. Отключает автоперезапуск
3. Убивает процесс через `sudo kill -9`
4. Удаляет контейнер
5. Проверяет результат

Скрипт находится в `scripts/remove_stuck_container.sh`.

### Альтернативные методы

#### Метод 1: Перезапуск Docker daemon

**⚠️ ВНИМАНИЕ:** Это остановит ВСЕ контейнеры на сервере!

```bash
# Для systemd
sudo systemctl restart docker

# Для snap
sudo snap restart docker
```

После перезапуска попробуйте удалить контейнер снова:

```bash
sudo docker rm -f <container_id>
```

#### Метод 2: Удаление через docker-compose

Если контейнер был запущен через docker-compose:

```bash
cd ~/ScribotV2/deployment
sudo docker-compose -f docker-compose.yml down --remove-orphans
sudo docker-compose -f docker-compose.prod.yml down --remove-orphans
```

#### Метод 3: Проверка и удаление всех связанных ресурсов

```bash
# Остановить все контейнеры с определенным именем
sudo docker stop $(sudo docker ps -a -q --filter name=scribot_bot) 2>/dev/null || true

# Удалить все контейнеры с определенным именем
sudo docker rm -f $(sudo docker ps -a -q --filter name=scribot_bot) 2>/dev/null || true

# Удалить все остановленные контейнеры (осторожно!)
# sudo docker container prune -f
```

### Профилактика

Чтобы избежать проблем с подвисшими контейнерами:

1. **Всегда отключайте автоперезапуск перед остановкой:**
   ```bash
   sudo docker update --restart=no <container_id>
   ```

2. **Используйте таймауты при остановке:**
   ```bash
   sudo docker stop --timeout=10 <container_id>
   ```

3. **Используйте docker-compose для управления контейнерами:**
   ```bash
   sudo docker-compose down --timeout 10
   ```

4. **Регулярно проверяйте и очищайте неиспользуемые ресурсы:**
   ```bash
   sudo docker system prune -a --volumes
   ```

### Полезные команды для диагностики

```bash
# Проверить статус контейнера
sudo docker inspect <container_id> --format '{{.State.Status}}'

# Проверить PID процесса
sudo docker inspect <container_id> --format '{{.State.Pid}}'

# Проверить автоперезапуск
sudo docker inspect <container_id> --format '{{.HostConfig.RestartPolicy.Name}}'

# Посмотреть логи контейнера
sudo docker logs <container_id> --tail=50

# Проверить использование ресурсов
sudo docker stats <container_id>
```

### Связанные проблемы

- **Permission denied при удалении:** Используйте `sudo kill -9 <PID>` перед `docker rm -f`
- **Контейнер автоматически перезапускается:** Отключите автоперезапуск через `docker update --restart=no`
- **Контейнер не останавливается:** Используйте `docker kill` вместо `docker stop`
- **Множественные контейнеры с одним именем:** Удаляйте все через `docker ps -a -q --filter name=<name>`

### Дополнительные ресурсы

- [Docker Troubleshooting Guide](https://docs.docker.com/config/daemon/#troubleshoot-the-daemon)
- [Docker Container Management](https://docs.docker.com/engine/reference/commandline/container/)

