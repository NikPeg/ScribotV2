# Управление переменными окружения в CI/CD

## Проблема

При добавлении новой переменной окружения в `core/settings.py` необходимо обновить её в нескольких местах CI/CD конфигурации:

1. В тестах (два места - для обычных тестов и тестов миграций)
2. В секции `env` для деплоя
3. В списке `envs` для передачи переменных через SSH

Это легко забыть, что приводит к ошибкам при деплое.

## Решение

Добавлены структурированные комментарии-напоминания и шаблон тестовых переменных в начале файла для упрощения синхронизации.

**Примечание:** GitHub Actions не поддерживает YAML anchors, поэтому переменные необходимо обновлять вручную в нескольких местах. Комментарии и шаблон помогают не забыть об этом.

## Структура

### 1. Тестовые переменные

Определяются в двух местах в job'е `test`:
- В шаге "Run tests" (строка ~78)
- В шаге "Test migrations" (строка ~84)

Оба места должны содержать одинаковый набор переменных. В начале файла есть комментарий-шаблон для удобства копирования.

```yaml
env:
  BOT_TOKEN: "test_token"
  CHANNEL_URL: "https://test.channel.url"
  # ... остальные переменные
```

### 2. Переменные для деплоя

Определяются в секции `env` job'а `deploy`:

```yaml
env:
  BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
  CHANNEL_URL: ${{ secrets.CHANNEL_URL }}
  # ... остальные переменные
```

### 3. Список переменных для SSH (envs)

Список имен переменных для передачи через SSH:

```yaml
envs: BOT_TOKEN,CHANNEL_URL,FEEDBACK_URL,...
```

## Как добавить новую переменную

### Шаг 1: Добавить в core/settings.py

Добавьте новую переменную в класс `Settings`:

```python
class Settings(BaseSettings):
    # ... существующие переменные
    new_variable: str = "default_value"
```

### Шаг 2: Обновить .env.example

Добавьте новую переменную в `.env.example` с комментарием:

```env
# Описание новой переменной
NEW_VARIABLE=default_value
```

### Шаг 3: Обновить CI/CD конфигурацию

#### 3.1. Если переменная нужна в тестах

Добавьте переменную в оба места тестов (в шагах "Run tests" и "Test migrations"):

```yaml
env:
  # ... существующие переменные
  NEW_VARIABLE: "test_value"
```

**Важно:** Обновите оба места, иначе тесты миграций могут упасть.

#### 3.2. Добавить в секцию env для деплоя

Найдите секцию `env` в job'е `deploy` (примерно строка 138) и добавьте:

```yaml
env:
  # ... существующие переменные
  NEW_VARIABLE: ${{ secrets.NEW_VARIABLE || 'default_value' }}
```

#### 3.3. Добавить в список envs

Найдите параметр `envs` в том же job'е (примерно строка 157) и добавьте имя переменной:

```yaml
envs: BOT_TOKEN,CHANNEL_URL,...,NEW_VARIABLE
```

### Шаг 4: Добавить в GitHub Secrets

Если переменная содержит секретные данные, добавьте её в GitHub Secrets:

1. Перейдите в Settings → Secrets and variables → Actions
2. Нажмите "New repository secret"
3. Добавьте имя и значение

## Чеклист при добавлении переменной

- [ ] Добавлена переменная в `core/settings.py`
- [ ] Добавлена переменная в `.env.example` с комментарием
- [ ] Если нужна в тестах: добавлена в `x-test-env` в `.github/workflows/ci-cd.yml`
- [ ] Добавлена в секцию `env` для деплоя в `.github/workflows/ci-cd.yml`
- [ ] Добавлена в список `envs` для деплоя в `.github/workflows/ci-cd.yml`
- [ ] Если секретная: добавлена в GitHub Secrets
- [ ] Обновлена документация (если необходимо)

## Примеры

### Пример 1: Простая переменная (не секретная)

**core/settings.py:**
```python
max_retries: int = 3
```

**.env.example:**
```env
# Максимальное количество попыток
MAX_RETRIES=3
```

**.github/workflows/ci-cd.yml:**
```yaml
# В x-test-env (если нужна в тестах):
x-test-env: &test-env
  # ...
  MAX_RETRIES: "3"

# В env для деплоя:
env:
  # ...
  MAX_RETRIES: ${{ secrets.MAX_RETRIES || '3' }}

# В envs:
envs: ...,MAX_RETRIES
```

### Пример 2: Секретная переменная

**core/settings.py:**
```python
api_key: str
```

**.env.example:**
```env
# API ключ для внешнего сервиса
API_KEY=your_api_key_here
```

**.github/workflows/ci-cd.yml:**
```yaml
# В x-test-env (если нужна в тестах):
x-test-env: &test-env
  # ...
  API_KEY: "test_api_key"

# В env для деплоя:
env:
  # ...
  API_KEY: ${{ secrets.API_KEY }}

# В envs:
envs: ...,API_KEY
```

**GitHub Secrets:**
- Добавить `API_KEY` с реальным значением

## Полезные ссылки

- [GitHub Actions - Environment variables](https://docs.github.com/en/actions/learn-github-actions/environment-variables)
- [YAML Anchors and Aliases](https://yaml.org/spec/1.2.2/#3222-anchors-and-aliases)
- [appleboy/ssh-action documentation](https://github.com/appleboy/ssh-action)

