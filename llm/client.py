"""
Клиент для интеграции с LLM API для генерации и улучшения синопсисов протоколов.
Использует OpenAI API для генерации высококачественных медицинских текстов.
"""

import os
from typing import Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from models.domain import (
    PKParameters,
    RegulatoryIssue,
    SampleSizeResult,
    StudyDesign,
    StudyInput,
)


# Базовый промпт для генерации синопсиса протокола исследования биоэквивалентности
SYNOPSIS_GENERATION_PROMPT = """
Ты — опытный медицинский писатель, специализирующийся на протоколах клинических исследований биоэквивалентности.
Твоя задача — создать детальный и профессиональный синопсис протокола исследования биоэквивалентности на русском языке.

Синопсис должен:
1. Быть написан в научном медицинском стиле
2. Соответствовать требованиям российских и международных регуляторных органов (Минздрав РФ, EMA, FDA)
3. Содержать все ключевые разделы: цели, задачи, дизайн, методологию, критерии включения/исключения
4. Быть конкретным и избегать общих фраз
5. Включать все технические детали исследования

Входные данные исследования:
{study_info}

Используй эту информацию для создания полного синопсиса протокола в формате Markdown.
Структура должна включать следующие разделы:
1. Название протокола
2. Цели исследования
3. Задачи исследования
4. Дизайн исследования
5. Популяция и критерии отбора (включая критерии включения и исключения)
6. Фармакокинетические параметры
7. Статистическая методология
8. План мониторинга безопасности
9. Биоаналитический метод
10. Расчёт размера выборки
11. Регуляторные замечания (если есть)

Создай профессиональный, детальный синопсис, который можно использовать как основу для реального протокола исследования.
"""


def _format_study_info(
    study_input: StudyInput,
    pk: PKParameters,
    design: StudyDesign,
    sample_size: SampleSizeResult,
    issues: list[RegulatoryIssue],
) -> str:
    """Форматирует информацию об исследовании для промпта."""
    
    info = f"""
Препарат: {study_input.inn}
Дозировка: {study_input.dose_mg} мг
Лекарственная форма: {study_input.form}
Режим приёма: {study_input.regime}

Фармакокинетические параметры:
- Cmax: {pk.cmax if pk.cmax is not None else 'не указан'} нг/мл
- AUC: {pk.auc if pk.auc is not None else 'не указан'} нг·ч/мл
- Tmax: {pk.tmax if pk.tmax is not None else 'не указан'} ч
- T½: {pk.t_half if pk.t_half is not None else 'не указан'} ч
- CVintra: {pk.cv_intra if pk.cv_intra is not None else 'не указан'}

Дизайн исследования:
- Тип: {design.name} ({design.type})
- Периоды: {design.periods}
- Последовательности: {', '.join(design.sequences)}
- Wash-out: {design.washout_days} дней
- RSABE применимо: {'Да' if design.rsabe_applicable else 'Нет'}

Параметры популяции:
- Возраст: {study_input.min_age}-{study_input.max_age} лет
- Пол: {study_input.sex}
- ИМТ: {study_input.bmi_min}-{study_input.bmi_max} кг/м²

Размер выборки:
- Базовый N: {sample_size.base_n}
- С учётом drop-out ({sample_size.dropout_rate:.0%}) и screen-fail ({sample_size.screen_fail_rate:.0%}): {sample_size.adjusted_for_dropout}
"""
    
    if issues:
        info += "\nРегуляторные замечания:\n"
        for issue in issues:
            info += f"- [{issue.severity}] {issue.code}: {issue.message}\n"
    
    return info


def generate_llm_synopsis(
    study_input: StudyInput,
    pk: PKParameters,
    design: StudyDesign,
    sample_size: SampleSizeResult,
    issues: list[RegulatoryIssue],
    api_key: Optional[str] = None,
    model: str = "gpt-4",
) -> str:
    """
    Генерирует синопсис протокола с использованием LLM.
    
    Args:
        study_input: Входные параметры исследования
        pk: Фармакокинетические параметры
        design: Дизайн исследования
        sample_size: Результаты расчёта размера выборки
        issues: Список регуляторных замечаний
        api_key: API ключ OpenAI (если не указан, берётся из переменной окружения)
        model: Модель для использования (по умолчанию gpt-4)
    
    Returns:
        Сгенерированный синопсис в формате Markdown
    
    Raises:
        RuntimeError: Если OpenAI библиотека не установлена
        Exception: При ошибках API
    """
    if not OPENAI_AVAILABLE:
        raise RuntimeError(
            "Библиотека openai не установлена. "
            "Установите её: pip install openai"
        )
    
    # Получаем API ключ
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "OpenAI API ключ не найден. "
            "Установите переменную окружения OPENAI_API_KEY или передайте api_key параметр."
        )
    
    # Создаём клиент OpenAI
    client = OpenAI(api_key=api_key)
    
    # Форматируем информацию об исследовании
    study_info = _format_study_info(study_input, pk, design, sample_size, issues)
    
    # Формируем полный промпт
    full_prompt = SYNOPSIS_GENERATION_PROMPT.format(study_info=study_info)
    
    # Делаем запрос к API
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты — опытный медицинский писатель, специализирующийся на протоколах клинических исследований."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        
        synopsis = response.choices[0].message.content
        return synopsis
        
    except Exception as e:
        raise Exception(f"Ошибка при генерации синопсиса через LLM: {str(e)}")


def enhance_synopsis_with_llm(
    base_synopsis: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4",
) -> str:
    """
    Улучшает существующий синопсис с помощью LLM.
    
    Args:
        base_synopsis: Базовый синопсис, созданный шаблонами
        api_key: API ключ OpenAI
        model: Модель для использования
    
    Returns:
        Улучшенный синопсис
    """
    if not OPENAI_AVAILABLE:
        raise RuntimeError(
            "Библиотека openai не установлена. "
            "Установите её: pip install openai"
        )
    
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "OpenAI API ключ не найден."
        )
    
    client = OpenAI(api_key=api_key)
    
    enhancement_prompt = f"""
Ниже представлен синопсис протокола исследования биоэквивалентности.
Улучши его, сделав более профессиональным и детальным, сохраняя все технические данные.

Улучшения должны включать:
1. Более точные медицинские формулировки
2. Дополнительные детали по методологии
3. Улучшенную структуру и читаемость
4. Соответствие медицинским стандартам написания

Базовый синопсис:

{base_synopsis}

Верни улучшенный синопсис в формате Markdown, сохранив все технические данные.
"""
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты — опытный медицинский редактор, улучшающий научные медицинские тексты."
                },
                {
                    "role": "user",
                    "content": enhancement_prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        
        enhanced_synopsis = response.choices[0].message.content
        return enhanced_synopsis
        
    except Exception as e:
        raise Exception(f"Ошибка при улучшении синопсиса через LLM: {str(e)}")
