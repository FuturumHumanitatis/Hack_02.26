# Ifarma BE Study Planner — прототип

AI-инструмент для планирования исследований биоэквивалентности (кейс Ifarma / SechenovTech).

## Возможности

- Автоматический подбор дизайна исследования (2×2, реплицированный, параллельный) по CVintra и T½
- Расчёт размера выборки (TOST, нормальное приближение) с поправкой на drop-out и screen-fail
- Регуляторные проверки (wash-out, минимальный N, RSABE и др.)
- Генерация синопсиса протокола в формате Markdown
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
api/main.py            — FastAPI-приложение
static/index.html      — UI-форма ввода параметров исследования
demo/example_workflow.py — демонстрация end-to-end сценария
```

## Быстрый старт

```bash
pip install -r requirements.txt

# Запустить демо
python demo/example_workflow.py

# Запустить API-сервер
uvicorn api.main:app --reload
# Открыть UI-форму в браузере: http://localhost:8000/
```

## Пример запроса к API

```bash
curl -X POST http://localhost:8000/design \
  -H "Content-Type: application/json" \
  -d '{"inn":"омепразол","dose_mg":20,"form":"capsule","cv_category":"low","regime":"fasted"}'
```

## Поток данных

```
StudyInput → PK-параметры → Дизайн → Размер выборки → Рег. проверки → Синопсис
```