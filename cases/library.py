"""
Библиотека прецедентов (Case-Based Reasoning).
Накапливает обезличенные прототипы исследований биоэквивалентности.
Поддерживает поиск похожих завершённых проектов по МНН и параметрам.
"""

import json
import os
from typing import Any, Dict, List, Optional

_CASES_FILE = os.path.join(os.path.dirname(__file__), "data.json")

# Стартовый набор обезличенных прецедентов
_DEFAULT_CASES: List[Dict[str, Any]] = [
    {
        "id": "case-001",
        "inn": "омепразол",
        "dose_mg": 20.0,
        "form": "capsule",
        "design": "2x2",
        "n_total": 24,
        "cv_intra": 0.22,
        "washout_days": 7,
        "regime": "fasted",
        "cmax_ratio": 1.03,
        "auc_ratio": 1.01,
        "result": "BE установлена",
        "year": 2022,
        "notes": "Стандартный 2-периодный кросс-оверный дизайн. CV низкая. Замечаний нет.",
        "regulatory": "Решение №85, EMA Guideline",
    },
    {
        "id": "case-002",
        "inn": "метформин",
        "dose_mg": 500.0,
        "form": "tablet",
        "design": "2x2",
        "n_total": 28,
        "cv_intra": 0.28,
        "washout_days": 7,
        "regime": "fed",
        "cmax_ratio": 0.98,
        "auc_ratio": 0.99,
        "result": "BE установлена",
        "year": 2023,
        "notes": "Приём после еды. Умеренная вариабельность. Дизайн 2x2 достаточен.",
        "regulatory": "Решение №85",
    },
    {
        "id": "case-003",
        "inn": "амоксициллин",
        "dose_mg": 500.0,
        "form": "capsule",
        "design": "2x2",
        "n_total": 24,
        "cv_intra": 0.20,
        "washout_days": 7,
        "regime": "fasted",
        "cmax_ratio": 1.05,
        "auc_ratio": 1.02,
        "result": "BE установлена",
        "year": 2021,
        "notes": "Низкая вариабельность. Небольшая выборка достаточна.",
        "regulatory": "Решение №85, EMA",
    },
    {
        "id": "case-004",
        "inn": "аторвастатин",
        "dose_mg": 20.0,
        "form": "tablet",
        "design": "2x3x3",
        "n_total": 36,
        "cv_intra": 0.38,
        "washout_days": 14,
        "regime": "fasted",
        "cmax_ratio": 1.08,
        "auc_ratio": 0.97,
        "result": "BE установлена",
        "year": 2023,
        "notes": "Высокая вариабельность Cmax. Применён реплицированный дизайн 3-периодный.",
        "regulatory": "Решение №85, RSABE",
    },
    {
        "id": "case-005",
        "inn": "варфарин",
        "dose_mg": 5.0,
        "form": "tablet",
        "design": "2x2",
        "n_total": 32,
        "cv_intra": 0.18,
        "washout_days": 21,
        "regime": "fasted",
        "cmax_ratio": 1.00,
        "auc_ratio": 1.01,
        "result": "BE установлена",
        "year": 2022,
        "notes": "Длинный T½ требует увеличенного wash-out до 21 дня.",
        "regulatory": "Решение №85, FDA",
    },
    {
        "id": "case-006",
        "inn": "клопидогрел",
        "dose_mg": 75.0,
        "form": "tablet",
        "design": "2x4",
        "n_total": 44,
        "cv_intra": 0.55,
        "washout_days": 14,
        "regime": "fasted",
        "cmax_ratio": 1.12,
        "auc_ratio": 1.04,
        "result": "BE установлена (RSABE)",
        "year": 2023,
        "notes": "Очень высокая вариабельность. 4-периодный реплицированный дизайн, RSABE.",
        "regulatory": "Решение №85, RSABE, EMA",
    },
]


def _load_cases() -> List[Dict[str, Any]]:
    """Загружает кейсы из файла или возвращает стандартный набор."""
    if os.path.exists(_CASES_FILE):
        try:
            with open(_CASES_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return list(_DEFAULT_CASES)


def _save_cases(cases: List[Dict[str, Any]]) -> None:
    """Сохраняет кейсы в файл."""
    with open(_CASES_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)


def get_all_cases() -> List[Dict[str, Any]]:
    """Возвращает все кейсы из библиотеки."""
    return _load_cases()


def search_similar_cases(
    inn: str,
    cv_intra: Optional[float] = None,
    design: Optional[str] = None,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Ищет похожие кейсы по МНН и параметрам.
    Возвращает до `limit` наиболее релевантных прецедентов.
    """
    cases = _load_cases()
    scored: List[tuple] = []

    inn_lower = inn.lower().strip()

    for case in cases:
        score = 0.0

        # Точное совпадение МНН
        case_inn = case.get("inn", "").lower()
        if case_inn == inn_lower:
            score += 10.0
        elif inn_lower in case_inn or case_inn in inn_lower:
            score += 4.0

        # Близость CV
        if cv_intra is not None and case.get("cv_intra") is not None:
            diff = abs(cv_intra - case["cv_intra"])
            if diff < 0.05:
                score += 5.0
            elif diff < 0.15:
                score += 2.0

        # Совпадение дизайна
        if design and case.get("design") == design:
            score += 3.0

        if score > 0:
            scored.append((score, case))

    # Сортируем по убыванию релевантности
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


def save_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Сохраняет новый обезличенный кейс в библиотеку.
    Возвращает сохранённый кейс с назначенным id.
    """
    cases = _load_cases()

    # Генерируем id
    existing_ids = {c.get("id", "") for c in cases}
    idx = len(cases) + 1
    while f"case-{idx:03d}" in existing_ids:
        idx += 1
    case_data["id"] = f"case-{idx:03d}"

    cases.append(case_data)
    _save_cases(cases)
    return case_data
