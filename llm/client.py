"""
Клиент для интеграции с YandexGPT API для генерации синопсисов протоколов
исследований биоэквивалентности.

Использует YandexGPT 5 PRO (gpt://{folder_id}/yandexgpt-5-pro/latest)
через REST API Yandex Cloud Foundation Models.

Аутентификация: API-ключ Yandex Cloud (Authorization: Api-Key <key>).
Для получения ключа: https://yandex.cloud/ru/docs/iam/operations/api-key/create
"""

import json
import os
from typing import Optional

try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from models.domain import (
    PKParameters,
    RegulatoryIssue,
    SampleSizeResult,
    StudyDesign,
    StudyInput,
)

# ─────────────────────────────────────────────────────────────────────────────
# YandexGPT endpoint
# ─────────────────────────────────────────────────────────────────────────────
YANDEX_GPT_API_URL = (
    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
)
YANDEX_GPT_MODEL_ID = "yandexgpt-5-pro"

# ─────────────────────────────────────────────────────────────────────────────
# Системный промпт — инструктирует YandexGPT действовать как медицинский
# писатель и строго следовать правилам заполнения синопсиса.
# ─────────────────────────────────────────────────────────────────────────────
SYNOPSIS_SYSTEM_PROMPT = (
    "Ты — опытный медицинский писатель, специализирующийся на протоколах "
    "клинических исследований биоэквивалентности. "
    "Приступай к заполнению синопсиса, строго следуя инструкциям ниже. "
    "Твой ответ должен быть безупречным с точки зрения медицинской и "
    "регуляторной терминологии. Не добавляй информацию, отсутствующую во "
    "входных данных (запрещены галлюцинации)."
)

# ─────────────────────────────────────────────────────────────────────────────
# Специальный промпт для заполнения синопсиса.
# Содержит полные инструкции по подстановке значений из JSON-данных
# исследования в шаблон протокола биоэквивалентности.
# ─────────────────────────────────────────────────────────────────────────────
SYNOPSIS_FILLING_INSTRUCTIONS = """
Инструкции по заполнению синопсиса протокола исследования биоэквивалентности

Общие принципы:
- «     » (пять пробелов) — сюда нужно вставить конкретное значение из входных данных.
- Текст в квадратных скобках, например [натощак/после еды] — выбери один из вариантов согласно полю design.food и вставь только выбранное слово без скобок и слеша.
- Текст, выделенный {.mark} — это служебные метки. Не удаляй и не изменяй их, если только внутри квадратных скобок не указано значение для замены. В случае замены метка {.mark} должна быть удалена; если данных нет — оставить неизменной.
- Используй только предоставленные данные. Запрещено добавлять факты, отсутствующие во входных данных.

Числовые форматы:
- Все проценты, количество дней, объёмы крови и т.п. округляй до целых чисел, если иное не требуется.
- Период полувыведения T½ указан в часах — используй значение pk_data.t_half_hours как есть.
- Вставляй значения без дополнительных единиц измерения, если они уже присутствуют в тексте.

Соответствия переменных:
- Название протокола, спонсор, центр, лаборатория → protocol_name, sponsor, site, lab.
- Исследуемый препарат, действующее вещество → test_drug.name, test_drug.substance.
- Цель: первый пробел — test_drug.name, второй — reference_drug.name; режим: натощак/после приема высококалорийной пищи по design.food.
- Задачи п.1: вставь test_drug.substance; п.4: вставь safety.ecg_parameter.
- Дизайн: тип из design.type; описание периодов — по алгоритму выбора дизайна:
    * "2×2 crossover" → «двухпериодного перекрестного исследования в двух группах с приемом однократной дозы»
    * "replicate 2x2x4" → «четырехпериодного репликативного перекрестного исследования в двух группах с двукратным приемом каждого препарата»
    * "replicate 2x3x3" → «трехпериодного частично репликативного перекрестного исследования»
    * "parallel" → «параллельного исследования в двух группах»
- Методология: screening_max_days, pk_period_days (дважды), washout_days, follow_up_days.
- Количество проб крови: blood_sampling.samples_per_period (дважды); объём одной пробы: blood_sampling.volume_per_sample_ml.
- Общий объём ФК: blood_sampling.total_blood_fk_ml; образцов: samples_per_period × 2 × n_enrolled.
- Объём для клин. анализов: blood_sampling.total_blood_clinical_ml; итого за всё исследование — сумма обоих.
- Отмывочный период: washout_days и t_half_hours (дважды).
- Визит последующего наблюдения: follow_up_days.
- Добровольцы: cv_intra_percent (и параметры cv_intra_param); n_enrolled; n_screened; dropout_percent; screen_fail_percent.
- Критерий 18: test_drug.substance; критерий 30: test_drug.name; критерий 8 (исключения): 2 × tmax и само tmax.
- Исследуемый и референтный препараты: все поля из test_drug и reference_drug.
- Продолжительность: total_duration_days, pk_period_days, washout_days, follow_up_days.
- ФК параметры: substance; первичные — pk_parameters.primary; вторичные — pk_parameters.secondary.
- Аналитический метод: в конце — test_drug.substance.
- Критерии БЭ: ci_level, lower_bound, upper_bound, alpha.
- Анализ безопасности: safety.ecg_parameter.
- Статистика: statistics.anova_factors.
- Рандомизация: sample_size.n_per_group.
- Этика: ethical.insurance_company.

Обработка отсутствующих данных:
Если параметр не предоставлен, оставь «     » без изменений. Не нарушай структуру документа.

Формат вывода:
Выведи полностью заполненный синопсис в формате Markdown с сохранением всех разделов, таблиц и заголовков. Не добавляй лишних пояснений — только готовый документ.
"""


def _build_study_json(
    study_input: StudyInput,
    pk: PKParameters,
    design: StudyDesign,
    sample_size: SampleSizeResult,
    issues: list[RegulatoryIssue],
) -> dict:
    """Формирует словарь данных исследования в формате, ожидаемом промптом."""
    form_label = {
        "tablet": "таблетку",
        "capsule": "капсулу",
        "solution": "мл раствора",
        "other": "единицу",
    }.get(study_input.form, "единицу")

    food = "натощак" if study_input.regime == "fasted" else "после еды"
    cv_pct = None
    if pk.cv_intra is not None:
        cv_pct = round(pk.cv_intra * 100)
    elif study_input.cv_intra is not None:
        cv_pct = round(study_input.cv_intra * 100)

    design_type_map = {
        "2x2": "2×2 crossover",
        "2x3x3": "replicate 2x3x3",
        "2x4": "replicate 2x2x4",
        "parallel": "parallel",
    }

    return {
        "protocol_name": f"Протокол исследования биоэквивалентности {study_input.inn} {study_input.dose_mg:.0f} мг",
        "test_drug": {
            "name": f"{study_input.inn} {study_input.dose_mg:.0f} мг ({form_label})",
            "substance": study_input.inn,
        },
        "reference_drug": {
            "name": f"{study_input.inn} (референтный препарат)",
            "substance": study_input.inn,
        },
        "design": {
            "type": design_type_map.get(design.type, "2×2 crossover"),
            "food": food,
            "washout_days": round(design.washout_days),
        },
        "pk_data": {
            "cv_intra_percent": cv_pct,
            "cv_intra_param": "Cmax и AUC0-t",
            "t_half_hours": pk.t_half,
            "tmax_value": pk.tmax,
        },
        "sample_size": {
            "n_enrolled": sample_size.adjusted_for_dropout,
            "n_screened": round(
                sample_size.adjusted_for_dropout
                / max(1 - sample_size.screen_fail_rate, 0.01)
            ),
            "dropout_percent": round(sample_size.dropout_rate * 100),
            "screen_fail_percent": round(sample_size.screen_fail_rate * 100),
            "n_per_group": round(sample_size.adjusted_for_dropout / 2),
        },
        "study_periods": {
            "screening_max_days": 14,
            "pk_period_days": 1,
            "follow_up_days": 14,
            "total_duration_days": (
                14 + design.periods * 1
                + (design.periods - 1) * round(design.washout_days)
                + 14
            ),
        },
        "pk_parameters": {
            "primary": ["Cmax", "AUC0-t"],
            "secondary": ["AUC0-inf", "Tmax", "T½", "Kel"],
        },
        "bioequivalence_criteria": {
            "ci_level": 90,
            "lower_bound": 80.00,
            "upper_bound": 125.00,
            "alpha": 0.05,
        },
        "safety": {
            "ecg_parameter": "QTc",
        },
        "statistics": {
            "anova_factors": "последовательность, период, добровольец (в последовательности), препарат",
        },
        "regulatory_issues": [
            {"code": i.code, "severity": i.severity, "message": i.message}
            for i in issues
        ],
    }


def generate_llm_synopsis(
    study_input: StudyInput,
    pk: PKParameters,
    design: StudyDesign,
    sample_size: SampleSizeResult,
    issues: list[RegulatoryIssue],
    api_key: Optional[str] = None,
    folder_id: Optional[str] = None,
    model: str = YANDEX_GPT_MODEL_ID,
) -> str:
    """
    Генерирует синопсис протокола с использованием YandexGPT 5 PRO.

    Args:
        study_input: Входные параметры исследования
        pk: Фармакокинетические параметры
        design: Дизайн исследования
        sample_size: Результаты расчёта размера выборки
        issues: Список регуляторных замечаний
        api_key: API-ключ Yandex Cloud; если не указан, берётся из
                 переменной окружения YANDEX_API_KEY
        folder_id: Идентификатор каталога Yandex Cloud; если не указан,
                   берётся из YANDEX_FOLDER_ID
        model: Идентификатор модели YandexGPT (по умолчанию yandexgpt-5-pro)

    Returns:
        Сгенерированный синопсис в формате Markdown

    Raises:
        RuntimeError: Если библиотека requests не установлена
        ValueError: Если не указан API-ключ или folder_id
        Exception: При ошибках API
    """
    if not REQUESTS_AVAILABLE:
        raise RuntimeError(
            "Библиотека requests не установлена. "
            "Установите её: pip install requests"
        )

    if api_key is None:
        api_key = os.getenv("YANDEX_API_KEY")
    if not api_key:
        raise ValueError(
            "API-ключ Yandex Cloud не найден. "
            "Укажите его в поле ввода или установите переменную окружения YANDEX_API_KEY."
        )

    if folder_id is None:
        folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not folder_id:
        raise ValueError(
            "Идентификатор каталога Yandex Cloud (folder_id) не найден. "
            "Укажите его в поле ввода или установите переменную окружения YANDEX_FOLDER_ID."
        )

    study_data = _build_study_json(study_input, pk, design, sample_size, issues)
    study_json = json.dumps(study_data, ensure_ascii=False, indent=2)

    user_message = (
        f"{SYNOPSIS_FILLING_INSTRUCTIONS}\n\n"
        f"Входные данные исследования (JSON):\n```json\n{study_json}\n```\n\n"
        "На основе этих данных заполни синопсис протокола исследования "
        "биоэквивалентности, следуя инструкциям выше. "
        "Выведи готовый документ в формате Markdown."
    )

    model_uri = f"gpt://{folder_id}/{model}/latest"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.3,
            "maxTokens": "8000",
        },
        "messages": [
            {"role": "system", "text": SYNOPSIS_SYSTEM_PROMPT},
            {"role": "user", "text": user_message},
        ],
    }

    try:
        resp = _requests.post(
            YANDEX_GPT_API_URL,
            headers=headers,
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        synopsis = result["result"]["alternatives"][0]["message"]["text"]
        return synopsis
    except _requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise Exception(
            f"Ошибка YandexGPT API (HTTP {exc.response.status_code if exc.response is not None else '?'}): {detail}"
        ) from exc
    except Exception as exc:
        raise Exception(f"Ошибка при генерации синопсиса через YandexGPT: {exc}") from exc


def enhance_synopsis_with_llm(
    base_synopsis: str,
    api_key: Optional[str] = None,
    folder_id: Optional[str] = None,
    model: str = YANDEX_GPT_MODEL_ID,
) -> str:
    """
    Улучшает существующий синопсис с помощью YandexGPT 5 PRO.

    Args:
        base_synopsis: Базовый синопсис, созданный шаблонами
        api_key: API-ключ Yandex Cloud
        folder_id: Идентификатор каталога Yandex Cloud
        model: Идентификатор модели YandexGPT

    Returns:
        Улучшенный синопсис в формате Markdown
    """
    if not REQUESTS_AVAILABLE:
        raise RuntimeError(
            "Библиотека requests не установлена. "
            "Установите её: pip install requests"
        )

    if api_key is None:
        api_key = os.getenv("YANDEX_API_KEY")
    if not api_key:
        raise ValueError("API-ключ Yandex Cloud не найден.")

    if folder_id is None:
        folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not folder_id:
        raise ValueError("Идентификатор каталога Yandex Cloud (folder_id) не найден.")

    enhancement_prompt = (
        "Ниже представлен синопсис протокола исследования биоэквивалентности.\n"
        "Улучши его, сделав более профессиональным и детальным, сохраняя все технические данные.\n\n"
        "Улучшения должны включать:\n"
        "1. Более точные медицинские формулировки\n"
        "2. Дополнительные детали по методологии\n"
        "3. Улучшенную структуру и читаемость\n"
        "4. Соответствие медицинским стандартам написания\n\n"
        f"Базовый синопсис:\n\n{base_synopsis}\n\n"
        "Верни улучшенный синопсис в формате Markdown, сохранив все технические данные."
    )

    model_uri = f"gpt://{folder_id}/{model}/latest"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.4,
            "maxTokens": "8000",
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты — опытный медицинский редактор, улучшающий научные медицинские тексты.",
            },
            {"role": "user", "text": enhancement_prompt},
        ],
    }

    try:
        resp = _requests.post(
            YANDEX_GPT_API_URL,
            headers=headers,
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        return result["result"]["alternatives"][0]["message"]["text"]
    except _requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise Exception(
            f"Ошибка YandexGPT API (HTTP {exc.response.status_code if exc.response is not None else '?'}): {detail}"
        ) from exc
    except Exception as exc:
        raise Exception(f"Ошибка при улучшении синопсиса через YandexGPT: {exc}") from exc
