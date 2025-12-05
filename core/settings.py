from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Определяет возможные уровни логирования в чат админа."""
    ALL = 'all'
    NONE = 'none'

class Settings(BaseSettings):
    bot_token: str
    chat_url: str
    feedback_url: str
    sos_url: str

    admin_id: int
    log_level: LogLevel = LogLevel.ALL

    # Обязательные каналы для подписки (разделенные запятыми)
    # Формат: @channel1,@channel2 или channel_id1,channel_id2
    required_channels: str = ""

    # Список примеров тем для работ.
    sample_works: list[str] = [
        "Влияние интернет-мемов на современную политику",
        "Супергерои и их вклад в развитие физической культуры и спорта",
        "Влияние кофе на продуктивность студентов в период сессии",
        "Социальная адаптация зомби в современном обществе (на примере сериала 'Ходячие мертвецы')",
        "Влияние аниме на формирование эстетических предпочтений молодежи",
        "Социальная роль пиццы в жизни студента",
        "Влияние смайликов на эффективность текстовых сообщений",
        "Как музыка из 'Гарри Поттера' влияет на уровень стресса у студентов",
        "Психологический портрет современного геймера",
        "Социальные сети как новая форма искусства",
        "Психология котов: почему они так любят коробки?",
        "Зомби-апокалипсис: теоретический анализ возможных сценариев",
        "Сравнительный анализ домашних питомцев: кто лучше — кошки или собаки?",
    ]

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'  # Игнорируем дополнительные поля из .env
    )
    llm_token: str

settings = Settings()


def get_required_channels() -> list[str]:
    """
    Возвращает список обязательных каналов для подписки.
    Каналы разделяются запятыми, пробелы удаляются.
    """
    if not settings.required_channels:
        return []
    return [ch.strip() for ch in settings.required_channels.split(",") if ch.strip()]
