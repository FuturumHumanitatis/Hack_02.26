#!/usr/bin/env python3
"""
Демонстрация работы LLM-генерации синопсиса протокола исследования биоэквивалентности.
"""

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.domain import StudyInput
from pk_data.source import get_pk_parameters
from design.logic import select_study_design
from stats.sample_size import calculate_sample_size
from reg.checks import run_regulatory_checks
from llm.client import generate_llm_synopsis
from config import LLM_MODEL


def main() -> None:
    """Демонстрация LLM-генерации синопсиса."""
    
    # 1. Формируем входные данные
    study = StudyInput(
        inn="омепразол",
        dose_mg=20.0,
        form="capsule",
        cv_category="low",
        regime="fasted",
    )
    
    print("═" * 70)
    print("  ДЕМОНСТРАЦИЯ: LLM-генерация синопсиса протокола исследования БЭ")
    print("═" * 70)
    print(f"\nМНН: {study.inn}  |  Доза: {study.dose_mg} мг  |  Форма: {study.form}")
    print(f"Режим: {study.regime}  |  CV-категория: {study.cv_category}")
    
    # 2. Получаем все необходимые данные
    pk = get_pk_parameters(study)
    design = select_study_design(study, pk)
    sample = calculate_sample_size(study, design)
    issues = run_regulatory_checks(study, pk, design, sample)
    
    print(f"\n── PK-параметры ──")
    print(f"  Cmax = {pk.cmax}  |  AUC = {pk.auc}  |  Tmax = {pk.tmax}")
    print(f"  T½ = {pk.t_half}  |  CVintra = {pk.cv_intra}")
    
    print(f"\n── Дизайн ──")
    print(f"  {design.name}  ({design.type})")
    print(f"  Периоды: {design.periods}  |  Последовательности: {design.sequences}")
    print(f"  Wash-out: {design.washout_days:.0f} дн.  |  RSABE: {design.rsabe_applicable}")
    
    print(f"\n── Размер выборки ──")
    print(f"  Базовый N: {sample.base_n}")
    print(f"  С учётом потерь: {sample.adjusted_for_dropout}")
    
    # 3. Проверяем наличие API ключа
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("\n" + "⚠" * 35)
        print("⚠️  ВНИМАНИЕ: OPENAI_API_KEY не найден в переменных окружения!")
        print("⚠️  Для работы LLM-генерации необходимо установить API ключ:")
        print("⚠️  export OPENAI_API_KEY='ваш-ключ'")
        print("⚠" * 35)
        print("\n❌  Демонстрация прервана.")
        return
    
    # 4. Генерируем синопсис через LLM
    print("\n── Генерация синопсиса через LLM ──")
    print("⏳  Отправка запроса к OpenAI API...")
    
    try:
        synopsis = generate_llm_synopsis(
            study, pk, design, sample, issues,
            api_key=api_key,
            model=LLM_MODEL
        )
        
        print("✅  Синопсис успешно сгенерирован через LLM!")
        
        # 5. Сохраняем результат
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "llm_synopsis_omeprazole.md",
        )
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(synopsis)
        
        print(f"\n📄  Синопсис сохранён в {output_path}")
        print(f"\n📊  Длина сгенерированного текста: {len(synopsis)} символов")
        
        # Показываем первые 500 символов
        print("\n" + "─" * 70)
        print("Предварительный просмотр (первые 500 символов):")
        print("─" * 70)
        print(synopsis[:500])
        if len(synopsis) > 500:
            print("...")
        print("─" * 70)
        
        print("\n✅  Демонстрация завершена успешно!")
        
    except Exception as e:
        print(f"\n❌  Ошибка при генерации синопсиса через LLM:")
        print(f"   {str(e)}")
        print("\n💡  Возможные причины:")
        print("   - Неверный API ключ")
        print("   - Проблемы с подключением к OpenAI API")
        print("   - Недостаточный баланс на аккаунте OpenAI")
        return
    
    print("═" * 70)


if __name__ == "__main__":
    main()
