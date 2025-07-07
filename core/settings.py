from pydantic_settings import BaseSettings, SettingsConfigDict

# Этот файл отвечает за загрузку и хранение всех настроек и секретов проекта.
# Мы используем pydantic-settings для автоматической валидации данных и загрузки
# переменных из .env файла.

class Settings(BaseSettings):
    """
    Класс для хранения настроек, загружаемых из переменных окружения.
    """
    # Токен для доступа к Telegram Bot API.
    # pydantic автоматически найдет переменную окружения BOT_TOKEN (без учета регистра)
    # и присвоит ее значение этому атрибуту.
    bot_token: str

    # Вложенный класс model_config используется для конфигурации поведения pydantic.
    model_config = SettingsConfigDict(
        # Указываем pydantic, что нужно искать файл .env в корне проекта
        env_file='.env',
        # Указываем кодировку файла .env
        env_file_encoding='utf-8'
    )


# Создаем единственный экземпляр класса Settings.
# Теперь, чтобы получить доступ к настройкам из любого другого файла,
# достаточно будет импортировать этот объект: from core.settings import settings
settings = Settings()
