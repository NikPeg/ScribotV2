import asyncio
from openai import AsyncOpenAI
from core import settings

# Инициализируем клиента OpenAI
client = AsyncOpenAI(api_key=settings.openai_api_key)

# Словарь для хранения ID ассистентов.
# Вы можете заранее создать их, скопировать ID из консоли
# и вставить сюда для ускорения первого запуска.
ASSISTANT_IDS = {
    "gpt-3.5-turbo": "asst_lAXuQ4InHOPz6L5YPuUxlaxt",
    "gpt-4o-mini": "asst_PMHKofEW6rucU4D6k5uJq4xF",
}

# Общий system prompt для всех ассистентов
COMMON_INSTRUCTIONS = (
    "Ты — эксперт по написанию студенческих работ. Твоя задача — генерировать "
    "содержимое для курсовых, дипломных и других работ в формате LaTeX. "
    "Следуй инструкциям пользователя, создавай структурированный и "
    "академически корректный текст. Генерируй только запрошенную часть, "
    "не добавляй лишних комментариев."
)

async def get_or_create_assistant_id(model_name: str) -> str:
    """
    Получает или создает ассистента для УКАЗАННОЙ МОДЕЛИ и возвращает его ID.
    """
    # Если ID для этой модели уже есть в кеше, возвращаем его
    if model_name in ASSISTANT_IDS:
        return ASSISTANT_IDS[model_name]

    # Если ID нет, создаем нового ассистента
    print(f"Ассистент для модели {model_name} не найден. Создаю нового...")
    assistant = await client.beta.assistants.create(
        name=f"Scribo Generator ({model_name})",
        instructions=COMMON_INSTRUCTIONS,
        model=model_name,
    )

    assistant_id = assistant.id
    ASSISTANT_IDS[model_name] = assistant_id # Сохраняем ID в кеш

    print(f"СОЗДАН НОВЫЙ АССИСТЕНТ. Модель: {model_name}, ID: {assistant_id}")
    print("Сохраните этот ID для будущих запусков, чтобы ускорить работу.")

    return assistant_id

async def create_thread() -> str:
    """Создает новый поток (thread) для диалога и возвращает его ID."""
    thread = await client.beta.threads.create()
    return thread.id

async def ask_assistant(thread_id: str, prompt: str, model_name: str) -> str:
    """
    Отправляет промпт в ассистент, ждет ответа и возвращает его.
    Теперь функция принимает model_name, чтобы выбрать правильного ассистента.
    """
    # Добавляем сообщение пользователя в поток
    await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    # Получаем ID ассистента для нужной модели
    assistant_id = await get_or_create_assistant_id(model_name)

    # Запускаем ассистента
    run = await client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    # Ожидаем завершения работы ассистента
    while run.status in ['queued', 'in_progress']:
        await asyncio.sleep(1)
        run = await client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )

    if run.status == 'completed':
        messages = await client.beta.threads.messages.list(thread_id=thread_id, limit=1)
        if messages.data:
            return messages.data[0].content[0].text.value

    print(f"Ошибка выполнения Run. Статус: {run.status}")
    print(f"Детали ошибки: {run.last_error}")
    return "Произошла ошибка при генерации ответа."
