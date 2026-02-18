# LLM Integration Guide

Этот документ описывает интеграцию LLM (Large Language Model) для генерации синопсисов протоколов исследований биоэквивалентности.

## Обзор

Проект поддерживает два режима генерации синопсиса:

1. **Шаблонная генерация** — быстрая генерация на основе предопределённых шаблонов
2. **LLM-генерация** — использование GPT-4 для создания более детальных и профессиональных текстов

## Настройка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

Это установит библиотеку `openai>=1.0.0` и другие необходимые пакеты.

### 2. Получение API ключа OpenAI

1. Зарегистрируйтесь на https://platform.openai.com/
2. Перейдите в раздел API Keys: https://platform.openai.com/api-keys
3. Создайте новый API ключ
4. Скопируйте ключ (он будет показан только один раз)

### 3. Установка API ключа

Установите переменную окружения `OPENAI_API_KEY`:

```bash
export OPENAI_API_KEY='sk-...'
```

Для постоянного использования, добавьте эту строку в `~/.bashrc` или `~/.zshrc`:

```bash
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
source ~/.bashrc
```

### 4. Конфигурация

В файле `config.py` доступны следующие настройки:

```python
# Включить/выключить использование LLM для генерации синопсиса
LLM_ENABLED = True

# Модель OpenAI для использования
LLM_MODEL = "gpt-4"

# Использовать шаблонную генерацию при ошибке LLM
LLM_FALLBACK_TO_TEMPLATE = True
```

## Использование

### 1. Через API

#### Шаблонная генерация (старый метод)

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

#### LLM-генерация (новый метод)

```bash
curl -X POST http://localhost:8000/design-llm \
  -H "Content-Type: application/json" \
  -d '{
    "inn": "омепразол",
    "dose_mg": 20,
    "form": "capsule",
    "cv_category": "low",
    "regime": "fasted"
  }'
```

Ответ будет содержать дополнительные поля:

```json
{
  "pk": { ... },
  "design": { ... },
  "sample_size": { ... },
  "issues": [ ... ],
  "synopsis_md": "# Синопсис...",
  "llm_generated": true,
  "error_message": null
}
```

- `llm_generated`: `true` если синопсис был сгенерирован через LLM, `false` если использовался fallback
- `error_message`: описание ошибки, если LLM недоступен (null при успешной генерации)

### 2. Через Python API

```python
from models.domain import StudyInput
from pk_data.source import get_pk_parameters
from design.logic import select_study_design
from stats.sample_size import calculate_sample_size
from reg.checks import run_regulatory_checks
from llm.client import generate_llm_synopsis

# Создаём входные данные
study = StudyInput(
    inn="омепразол",
    dose_mg=20.0,
    form="capsule",
    cv_category="low",
    regime="fasted",
)

# Получаем все необходимые данные
pk = get_pk_parameters(study)
design = select_study_design(study, pk)
sample = calculate_sample_size(study, design)
issues = run_regulatory_checks(study, pk, design, sample)

# Генерируем синопсис через LLM
synopsis = generate_llm_synopsis(
    study, pk, design, sample, issues,
    api_key=None,  # Использует OPENAI_API_KEY из окружения
    model="gpt-4"
)

print(synopsis)
```

### 3. Через демо-скрипт

```bash
# Убедитесь, что OPENAI_API_KEY установлен
export OPENAI_API_KEY='sk-...'

# Запустите демо
python demo/llm_demo.py
```

Скрипт:
- Проверит наличие API ключа
- Соберёт все необходимые данные об исследовании
- Отправит запрос к OpenAI API
- Сохранит результат в `llm_synopsis_omeprazole.md`

## Промпт для генерации

LLM использует специально разработанный промпт (см. `llm/client.py`), который инструктирует модель:

- Создавать медицинский текст в соответствии с требованиями регуляторов (Минздрав РФ, EMA, FDA)
- Включать все необходимые разделы протокола
- Использовать профессиональные медицинские формулировки
- Структурировать документ в формате Markdown

Промпт получает на вход:
- Параметры препарата (МНН, дозировка, форма)
- Фармакокинетические параметры
- Дизайн исследования
- Размер выборки
- Регуляторные замечания

## Обработка ошибок

### 1. Отсутствует API ключ

**Ошибка**: `OPENAI_API_KEY не установлен`

**Решение**:
```bash
export OPENAI_API_KEY='sk-...'
```

### 2. Недостаточный баланс на аккаунте

**Ошибка**: `Insufficient quota` или подобное

**Решение**:
- Пополните баланс на https://platform.openai.com/account/billing
- Проверьте лимиты использования API

### 3. Проблемы с сетью

**Ошибка**: `Connection error` или timeout

**Решение**:
- Проверьте подключение к интернету
- Убедитесь, что OpenAI API доступен из вашей сети
- При необходимости настройте прокси

### 4. Fallback к шаблонной генерации

Если `LLM_FALLBACK_TO_TEMPLATE = True` (по умолчанию), при любой ошибке LLM система автоматически переключится на шаблонную генерацию.

Чтобы отключить fallback и получать ошибки:

```python
# config.py
LLM_FALLBACK_TO_TEMPLATE = False
```

## Сравнение методов генерации

| Характеристика | Шаблонная генерация | LLM-генерация |
|----------------|---------------------|---------------|
| Скорость | Мгновенная (~1 мс) | ~5-15 секунд |
| Стоимость | Бесплатно | ~$0.03-0.12 за запрос |
| Качество текста | Базовое, шаблонное | Высокое, профессиональное |
| Детализация | Стандартная | Улучшенная |
| Требования | Нет | API ключ OpenAI |
| Надёжность | 100% | Зависит от доступности API |

## Стоимость использования

При использовании GPT-4:
- Input: ~$0.03 за 1K токенов
- Output: ~$0.06 за 1K токенов
- Типичный запрос: ~500 input tokens + ~2000 output tokens
- **Стоимость одного синопсиса**: ~$0.14 (0.5 * $0.03 + 2.0 * $0.06)

Для снижения стоимости можно использовать GPT-3.5-turbo:

```python
synopsis = generate_llm_synopsis(
    ...,
    model="gpt-3.5-turbo"  # Дешевле в ~10 раз
)
```

## Улучшение синопсиса

Помимо полной генерации, доступна функция улучшения существующего синопсиса:

```python
from synopsis.generator import generate_synopsis_markdown
from llm.client import enhance_synopsis_with_llm

# Создаём базовый синопсис шаблонами
base_synopsis = generate_synopsis_markdown(study, pk, design, sample, issues)

# Улучшаем его через LLM
enhanced_synopsis = enhance_synopsis_with_llm(
    base_synopsis,
    api_key=None,
    model="gpt-4"
)
```

Это полезно когда:
- Нужно сохранить все технические данные из шаблона
- Требуется улучшить только стиль и формулировки
- Хочется сэкономить на токенах (меньше input данных)

## Разработка и тестирование

### Тестирование без API ключа

Для тестирования без реальных вызовов к OpenAI:

```python
# Установите fallback режим
LLM_FALLBACK_TO_TEMPLATE = True

# Или явно обработайте отсутствие ключа
try:
    synopsis = generate_llm_synopsis(...)
except ValueError as e:
    print(f"LLM недоступен: {e}")
    # Используйте шаблонную генерацию
    synopsis = generate_synopsis_markdown(...)
```

### Логирование

Для отладки можно добавить логирование запросов:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Теперь OpenAI библиотека будет выводить детальные логи
```

## Безопасность

### Не коммитьте API ключи!

❌ **Никогда не коммитьте API ключи в репозиторий:**

```python
# НЕ ДЕЛАЙТЕ ТАК!
api_key = "sk-..."
```

✅ **Используйте переменные окружения:**

```python
import os
api_key = os.getenv("OPENAI_API_KEY")
```

### .gitignore

Убедитесь, что `.env` файлы исключены:

```
.env
.env.local
*.key
```

## Поддержка и вопросы

При возникновении проблем:

1. Проверьте, что API ключ установлен: `echo $OPENAI_API_KEY`
2. Проверьте баланс аккаунта OpenAI
3. Проверьте логи ошибок в выводе программы
4. Попробуйте режим fallback для отладки
5. Обратитесь к документации OpenAI: https://platform.openai.com/docs

## Roadmap

Планируемые улучшения:

- [ ] Поддержка других LLM провайдеров (Anthropic Claude, local models)
- [ ] Кэширование результатов для экономии
- [ ] Батч-обработка нескольких синопсисов
- [ ] Настройка промптов через конфигурацию
- [ ] Поддержка разных языков вывода
- [ ] Асинхронные запросы к API
