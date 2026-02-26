# LLM Integration Guide — YandexGPT 5 PRO

Этот документ описывает интеграцию **YandexGPT 5 PRO** для генерации синопсисов протоколов исследований биоэквивалентности.

## Обзор

Проект поддерживает два режима генерации синопсиса:

1. **Шаблонная генерация** — мгновенная генерация на основе предопределённых шаблонов (кнопка «Рассчитать план исследования»)
2. **LLM-генерация** — использование YandexGPT 5 PRO для создания детальных профессиональных синопсисов (кнопка «✨ Сгенерировать с YandexGPT 5 PRO»)

### Схема работы

```
Пользователь вводит данные исследования
        ↓
Система собирает PK-параметры, дизайн, размер выборки
        ↓
Данные форматируются в JSON и передаются вместе со
специальными инструкциями по заполнению синопсиса
        ↓
YandexGPT 5 PRO генерирует профессиональный синопсис
        ↓
Синопсис отображается пользователю
```

### Специальный промпт

Для генерации синопсиса используется специально разработанный промпт (`SYNOPSIS_FILLING_INSTRUCTIONS` в `llm/client.py`), который инструктирует модель:

- Заполнять все разделы синопсиса данными из JSON
- Соблюдать медицинскую и регуляторную терминологию (Минздрав РФ, EMA, FDA)
- Не добавлять информацию, отсутствующую во входных данных (запрет галлюцинаций)
- Сохранять структуру документа со всеми разделами и таблицами
- Использовать правильные числовые форматы (проценты, дни, объёмы)

---

## Настройка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

Это установит библиотеку `requests>=2.28` и другие необходимые пакеты.

### 2. Получение учётных данных Yandex Cloud

Для работы с YandexGPT 5 PRO необходимы два параметра:

#### 2.1. API-ключ Yandex Cloud

1. Войдите в консоль Yandex Cloud: https://console.yandex.cloud/
2. Выберите нужный сервисный аккаунт или создайте новый
3. Перейдите в раздел **IAM → Сервисные аккаунты → {ваш аккаунт} → API-ключи**
4. Нажмите «Создать API-ключ»
5. Скопируйте секретный ключ (показывается только один раз)
6. Документация: https://yandex.cloud/ru/docs/iam/operations/api-key/create

#### 2.2. Идентификатор каталога (Folder ID)

1. В консоли Yandex Cloud откройте нужный каталог
2. Folder ID отображается в адресной строке или на странице каталога
3. Документация: https://yandex.cloud/ru/docs/resource-manager/operations/folder/get-id

### 3. Ввод ключей через UI

В интерфейсе приложения:

1. Заполните форму с параметрами исследования (МНН, дозировка и т.д.)
2. В разделе **«YandexGPT 5 PRO — генерация синопсиса»** введите:
   - **API-ключ Yandex Cloud** (поле `API-ключ Yandex Cloud`)
   - **Идентификатор каталога** (поле `Folder ID`)
3. Нажмите кнопку **«✨ Сгенерировать с YandexGPT 5 PRO»**

> 🔒 Ключи используются только в рамках одного запроса и не сохраняются.

### 4. Настройка через переменные окружения

Для серверного развёртывания без UI-ввода:

```bash
export YANDEX_API_KEY='AQVN...'
export YANDEX_FOLDER_ID='b1g...'
```

Для постоянного использования, добавьте в `~/.bashrc`:

```bash
echo 'export YANDEX_API_KEY="AQVN..."' >> ~/.bashrc
echo 'export YANDEX_FOLDER_ID="b1g..."' >> ~/.bashrc
source ~/.bashrc
```

### 5. Конфигурация (`config.py`)

```python
LLM_ENABLED = True                  # Включить LLM-генерацию
LLM_MODEL = "yandexgpt-5-pro"       # Модель YandexGPT
LLM_FALLBACK_TO_TEMPLATE = True     # Fallback на шаблоны при ошибке LLM
```

---

## Использование

### 1. Через UI (рекомендуется)

1. Откройте приложение в браузере
2. Заполните параметры исследования
3. Введите API-ключ и Folder ID в разделе YandexGPT
4. Нажмите **«✨ Сгенерировать с YandexGPT 5 PRO»**
5. После генерации доступны кнопки экспорта (DOCX, PDF, перевод на английский)

### 2. Через API

#### Эндпоинт `/design-llm`

```bash
curl -X POST http://localhost:8000/design-llm \
  -H "Content-Type: application/json" \
  -d '{
    "inn": "омепразол",
    "dose_mg": 20,
    "form": "capsule",
    "cv_category": "low",
    "regime": "fasted",
    "api_key": "AQVN...",
    "folder_id": "b1g..."
  }'
```

Ответ содержит дополнительные поля:

```json
{
  "pk": { ... },
  "design": { ... },
  "sample_size": { ... },
  "issues": [ ... ],
  "synopsis_md": "# Синопсис протокола...",
  "llm_generated": true,
  "error_message": null
}
```

- `llm_generated`: `true` — синопсис создан YandexGPT; `false` — использован шаблон
- `error_message`: описание ошибки (null при успешной генерации)

#### Шаблонная генерация (без LLM)

```bash
curl -X POST http://localhost:8000/design \
  -H "Content-Type: application/json" \
  -d '{
    "inn": "омепразол",
    "dose_mg": 20,
    "form": "capsule",
    "cv_category": "low",
    "regime": "fasted"
  }'
```

### 3. Через Python API

```python
from models.domain import StudyInput
from pk_data.source import get_pk_parameters
from design.logic import select_study_design
from stats.sample_size import calculate_sample_size
from reg.checks import run_regulatory_checks
from llm.client import generate_llm_synopsis

study = StudyInput(
    inn="омепразол",
    dose_mg=20.0,
    form="capsule",
    cv_category="low",
    regime="fasted",
)

pk = get_pk_parameters(study)
design = select_study_design(study, pk)
sample = calculate_sample_size(study, design)
issues = run_regulatory_checks(study, pk, design, sample)

synopsis = generate_llm_synopsis(
    study, pk, design, sample, issues,
    api_key="AQVN...",    # или None — тогда берётся из YANDEX_API_KEY
    folder_id="b1g...",   # или None — тогда берётся из YANDEX_FOLDER_ID
    model="yandexgpt-5-pro",
)

print(synopsis)
```

---

## Техническая реализация

### API-эндпоинт YandexGPT

- **URL**: `https://llm.api.cloud.yandex.net/foundationModels/v1/completion`
- **Метод**: `POST`
- **Аутентификация**: `Authorization: Api-Key {api_key}`
- **Модель**: `gpt://{folder_id}/yandexgpt-5-pro/latest`

### Параметры запроса

```json
{
  "modelUri": "gpt://{folder_id}/yandexgpt-5-pro/latest",
  "completionOptions": {
    "stream": false,
    "temperature": 0.3,
    "maxTokens": "8000"
  },
  "messages": [
    {"role": "system", "text": "...системный промпт..."},
    {"role": "user",   "text": "...инструкции + JSON данных..."}
  ]
}
```

### Входные данные для LLM (JSON-формат)

Система автоматически формирует следующую JSON-структуру из параметров исследования:

```json
{
  "protocol_name": "Протокол исследования биоэквивалентности омепразол 20 мг",
  "test_drug": { "name": "омепразол 20 мг (капсулу)", "substance": "омепразол" },
  "reference_drug": { "name": "омепразол (референтный препарат)" },
  "design": { "type": "2×2 crossover", "food": "натощак", "washout_days": 7 },
  "pk_data": { "cv_intra_percent": 25, "t_half_hours": 1.0, "tmax_value": 1.0 },
  "sample_size": { "n_enrolled": 24, "dropout_percent": 20, ... },
  "study_periods": { "screening_max_days": 14, "pk_period_days": 1, ... },
  "bioequivalence_criteria": { "ci_level": 90, "lower_bound": 80.0, "upper_bound": 125.0 },
  ...
}
```

---

## Обработка ошибок и Fallback

| Ситуация | Поведение |
|----------|-----------|
| API-ключ/Folder ID не указаны | Fallback → шаблонная генерация + предупреждение |
| Ошибка сети | Fallback → шаблонная генерация + сообщение об ошибке |
| Ошибка HTTP API YandexGPT | Fallback → шаблонная генерация + сообщение об ошибке |
| `LLM_FALLBACK_TO_TEMPLATE = False` | HTTP 500 при любой ошибке LLM |

### Отключение Fallback

Чтобы получать явные ошибки вместо шаблонного синопсиса:

```python
# config.py
LLM_FALLBACK_TO_TEMPLATE = False
```

---

## Сравнение методов генерации

| Характеристика | Шаблонная генерация | YandexGPT 5 PRO |
|----------------|---------------------|-----------------|
| Скорость | Мгновенная (~1 мс) | ~10–30 секунд |
| Требования | Нет | API-ключ + Folder ID |
| Качество текста | Базовое, шаблонное | Высокое, профессиональное |
| Медицинская точность | Стандартная | Улучшенная |
| Надёжность | 100% | Зависит от доступности API |
| Стоимость | Бесплатно | По тарифам Yandex Cloud |

---

## Безопасность

### ❌ Никогда не коммитьте ключи в репозиторий

```python
# НЕ ДЕЛАЙТЕ ТАК!
api_key = "AQVN..."
```

### ✅ Используйте переменные окружения или UI-ввод

```python
import os
api_key = os.getenv("YANDEX_API_KEY")
```

Ключи, введённые через UI, передаются только в рамках одного HTTPS-запроса и не сохраняются на сервере.

### .gitignore

Убедитесь, что `.env` файлы исключены:

```
.env
.env.local
*.key
```

---

## Тестирование без реального API-ключа

При `LLM_FALLBACK_TO_TEMPLATE = True` (по умолчанию) система автоматически переключается на шаблонную генерацию:

```python
from llm.client import generate_llm_synopsis

try:
    synopsis = generate_llm_synopsis(
        study, pk, design, sample, issues,
        api_key=None,    # не задан → ValueError → fallback
        folder_id=None,
    )
except ValueError as e:
    print(f"LLM недоступен: {e}")
    from synopsis.generator import generate_synopsis_markdown
    synopsis = generate_synopsis_markdown(study, pk, design, sample, issues)
```

---

## Поддержка и вопросы

При возникновении проблем:

1. Проверьте корректность API-ключа и Folder ID в консоли Yandex Cloud
2. Убедитесь, что у сервисного аккаунта есть роль `ai.languageModels.user`
3. Проверьте логи ошибок в выводе сервера
4. Используйте шаблонную генерацию для отладки
5. Документация YandexGPT: https://yandex.cloud/ru/docs/foundation-models/concepts/yandexgpt/

