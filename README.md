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

---

## Деплой — бесплатный публичный доступ

### Вариант 1: Render.com (рекомендуется, без кредитной карты)

1. Запушьте репозиторий на GitHub (или форкните его).
2. Зарегистрируйтесь на [render.com](https://render.com).
3. Нажмите **New → Web Service** → выберите репозиторий.
4. Render автоматически подхватит `render.yaml` из корня репозитория.  
   Нажмите **Create Web Service** — сборка и деплой запустятся автоматически.
5. Через ~2 минуты приложение будет доступно по адресу вида  
   `https://ifarma-be-planner.onrender.com`.

> **Бесплатный план**: 750 ч/мес, засыпает после 15 мин бездействия (первый запрос будет медленнее ~30 с).  
> Чтобы убрать задержку — перейдите на план Starter ($7/мес) или используйте Uptime Robot для ping каждые 10 мин.

---

### Вариант 2: Docker на собственном VPS / VPN-сервере

Если у вас есть VPS или VPN-сервер с публичным IP:

```bash
# На сервере (Ubuntu/Debian)
apt-get update && apt-get install -y docker.io

# Клонировать репозиторий
git clone https://github.com/<ваш-аккаунт>/Hack_02.26.git
cd Hack_02.26

# Собрать образ и запустить
docker build -t ifarma-be .
docker run -d --restart=always -p 80:8000 \
  -e OPENAI_API_KEY=ваш_ключ \   # необязательно
  --name ifarma ifarma-be

# Сервис будет доступен по http://<IP-сервера>/
```

Для HTTPS добавьте Nginx + Let's Encrypt (certbot).

---

### Вариант 3: Hugging Face Spaces (бесплатно, без регистрации карты)

1. Зарегистрируйтесь на [huggingface.co](https://huggingface.co).
2. Создайте новый **Space** → тип **Docker**.
3. Загрузите файлы репозитория (или подключите GitHub).
4. Space автоматически соберёт образ из `Dockerfile` и опубликует приложение.