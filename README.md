# Ifarma BE Study Planner — прототип

AI-инструмент для планирования исследований биоэквивалентности (кейс Ifarma / SechenovTech).

## Возможности

- Автоматический подбор дизайна исследования (2×2, реплицированный, параллельный) по CVintra и T½
- Расчёт размера выборки (TOST, нормальное приближение) с поправкой на drop-out и screen-fail
- Регуляторные проверки (wash-out, минимальный N, RSABE и др.)
- Генерация синопсиса протокола в формате Markdown
- **LLM-генерация синопсиса** — использование GPT-4 для создания профессиональных медицинских текстов
- REST API (FastAPI) для интеграции

## Структура проекта

```
config.py              — настройки и константы
models/domain.py       — Pydantic-модели (StudyInput, PKParameters, StudyDesign, …)
pk_data/source.py      — мини-БД PK-параметров (заглушка для хакатона)
design/logic.py        — логика выбора дизайна
stats/sample_size.py   — расчёт размера выборки
reg/checks.py          — регуляторные проверки
synopsis/templates.py  — текстовые шаблоны (русский язык)
synopsis/generator.py  — генерация Markdown-синопсиса
llm/client.py          — интеграция с LLM API (OpenAI GPT-4)
api/main.py            — FastAPI-приложение
static/index.html      — UI-форма ввода параметров исследования
demo/example_workflow.py — демонстрация end-to-end сценария
demo/llm_demo.py       — демонстрация LLM-генерации синопсиса
```

## Быстрый старт

```bash
pip install -r requirements.txt

# Запустить демо (шаблонная генерация)
python demo/example_workflow.py

# Запустить демо LLM-генерации (требуется OpenAI API ключ)
export OPENAI_API_KEY='ваш-ключ'
python demo/llm_demo.py

# Запустить API-сервер
uvicorn api.main:app --reload
# Открыть UI-форму в браузере: http://localhost:8000/
```

## LLM-интеграция

Проект поддерживает два режима генерации синопсиса:

1. **Шаблонная генерация** (`/design`) — быстрая генерация на основе предопределённых шаблонов
2. **LLM-генерация** (`/design-llm`) — использование GPT-4 для создания более детальных и профессиональных текстов

### Настройка LLM

1. Получите API ключ OpenAI: https://platform.openai.com/api-keys
2. Установите переменную окружения:
   ```bash
   export OPENAI_API_KEY='ваш-ключ'
   ```
3. Настройки в `config.py`:
   - `LLM_ENABLED` — включить/выключить LLM
   - `LLM_MODEL` — модель для использования (по умолчанию `gpt-4`)
   - `LLM_FALLBACK_TO_TEMPLATE` — использовать шаблоны при ошибке LLM

### Промпт для генерации синопсиса

LLM использует специально разработанный промпт, который инструктирует модель создавать:
- Медицинский текст в соответствии с требованиями Минздрава РФ, EMA и FDA
- Детальное описание всех разделов протокола исследования
- Профессиональные формулировки с учётом медицинских стандартов
- Структурированный Markdown-документ

## Пример запроса к API

### Шаблонная генерация
```bash
curl -X POST http://localhost:8000/design \
  -H "Content-Type: application/json" \
  -d '{"inn":"омепразол","dose_mg":20,"form":"capsule","cv_category":"low","regime":"fasted"}'
```

### LLM-генерация
```bash
curl -X POST http://localhost:8000/design-llm \
  -H "Content-Type: application/json" \
  -d '{"inn":"омепразол","dose_mg":20,"form":"capsule","cv_category":"low","regime":"fasted"}'
```

## Поток данных

```
StudyInput → PK-параметры → Дизайн → Размер выборки → Рег. проверки → Синопсис
                                                                           ↓
                                                              [Шаблоны или LLM]
```