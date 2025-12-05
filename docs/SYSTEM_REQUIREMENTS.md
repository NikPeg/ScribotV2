# Системные требования для ScribotV2

## Необходимые системные пакеты

Для полной работы генератора курсовых работ необходимо установить следующие системные пакеты:

### 1. LaTeX (для компиляции PDF)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install texlive-full texlive-lang-cyrillic
```

**macOS:**
```bash
brew install --cask mactex
```

**Windows:**
Скачайте и установите MiKTeX с официального сайта: https://miktex.org/

### 2. LibreOffice (для конвертации PDF в DOCX)

**Ubuntu/Debian:**
```bash
sudo apt-get install libreoffice
```

**macOS:**
```bash
brew install --cask libreoffice
```

После установки LibreOffice будет доступен по пути:
`/Applications/LibreOffice.app/Contents/MacOS/soffice`

**Windows:**
Скачайте и установите LibreOffice с официального сайта: https://www.libreoffice.org/

## Проверка установки

После установки проверьте доступность команд:

```bash
# Проверка LaTeX
pdflatex --version

# Проверка LibreOffice
# На Linux/Windows:
libreoffice --version

# На macOS:
/Applications/LibreOffice.app/Contents/MacOS/soffice --version
```

## Альтернативные решения

Если LibreOffice недоступен, DOCX файлы не будут создаваться, но PDF и TEX файлы будут работать нормально.

## Примечания

- LaTeX компиляция может занять некоторое время при первом запуске
- Убедитесь, что у системы достаточно места для временных файлов
- Рекомендуется минимум 2GB свободного места для работы с LaTeX