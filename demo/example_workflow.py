#!/usr/bin/env python3
"""
End-to-end пример: планирование исследования биоэквивалентности омепразола.
"""

import json
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.domain import StudyInput
from pk_data.source import get_pk_parameters
from design.logic import select_study_design
from stats.sample_size import calculate_sample_size
from reg.checks import run_regulatory_checks
from synopsis.generator import generate_synopsis_markdown


def main() -> None:
    # 1. Формируем входные данные
    study = StudyInput(
        inn="омепразол",
        dose_mg=20.0,
        form="capsule",
        cv_category="low",
        regime="fasted",
    )
    print("═" * 60)
    print("  ДЕМОНСТРАЦИЯ: Планирование исследования БЭ")
    print("═" * 60)
    print(f"\nМНН: {study.inn}  |  Доза: {study.dose_mg} мг  |  Форма: {study.form}")
    print(f"Режим: {study.regime}  |  CV-категория: {study.cv_category}")

    # 2. Получаем PK-параметры
    pk = get_pk_parameters(study)
    print(f"\n── PK-параметры ──")
    print(f"  Cmax = {pk.cmax}  |  AUC = {pk.auc}  |  Tmax = {pk.tmax}")
    print(f"  T½ = {pk.t_half}  |  CVintra = {pk.cv_intra}")

    # 3. Выбираем дизайн
    design = select_study_design(study, pk)
    print(f"\n── Дизайн ──")
    print(f"  {design.name}  ({design.type})")
    print(f"  Периоды: {design.periods}  |  Последовательности: {design.sequences}")
    print(f"  Wash-out: {design.washout_days:.0f} дн.  |  RSABE: {design.rsabe_applicable}")

    # 4. Рассчитываем размер выборки
    sample = calculate_sample_size(study, design)
    print(f"\n── Размер выборки ──")
    print(f"  Базовый N: {sample.base_n}")
    print(f"  С учётом потерь: {sample.adjusted_for_dropout}")

    # 5. Регуляторные проверки
    issues = run_regulatory_checks(study, pk, design, sample)
    print(f"\n── Регуляторные замечания ({len(issues)}) ──")
    for iss in issues:
        print(f"  [{iss.severity.upper()}] {iss.code}: {iss.message}")
    if not issues:
        print("  Замечаний нет.")

    # 6. Генерируем синопсис
    synopsis = generate_synopsis_markdown(study, pk, design, sample, issues)
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "example_synopsis_omeprazole.md",
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(synopsis)
    print(f"\n✅  Синопсис сохранён в {output_path}")
    print("═" * 60)


if __name__ == "__main__":
    main()
