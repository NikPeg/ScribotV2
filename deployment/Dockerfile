FROM python:3.11-slim

# Установка системных зависимостей для LaTeX и LibreOffice
# Используем минимальный набор LaTeX пакетов вместо texlive-full (экономит ~3GB и время сборки)
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-lang-cyrillic \
    libreoffice \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY . .

# Запускаем приложение
CMD ["python", "main.py"]

