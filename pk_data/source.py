"""
Модуль получения фармакокинетических параметров.

Для хакатона: локальная мини-БД (dict) с несколькими МНН.
В будущем можно подключить PubMed API, DrugBank или внутреннюю БД компании.
"""

from typing import Dict

from models.domain import PKParameters, StudyInput

# Условные данные для демонстрации — значения приближены к реальным,
# но не являются точными литературными значениями.
HARDCODED_PK_DB: Dict[str, PKParameters] = {
    "омепразол": PKParameters(
        cmax=580.0,    # нг/мл
        auc=1200.0,    # нг·ч/мл
        tmax=1.5,      # ч
        t_half=1.0,    # ч
        cv_intra=0.25,
    ),
    "omeprazole": PKParameters(
        cmax=580.0,
        auc=1200.0,
        tmax=1.5,
        t_half=1.0,
        cv_intra=0.25,
    ),
    "метопролол": PKParameters(
        cmax=50.0,
        auc=350.0,
        tmax=1.5,
        t_half=3.5,
        cv_intra=0.35,
    ),
    "metoprolol": PKParameters(
        cmax=50.0,
        auc=350.0,
        tmax=1.5,
        t_half=3.5,
        cv_intra=0.35,
    ),
    "амоксициллин": PKParameters(
        cmax=8000.0,
        auc=25000.0,
        tmax=1.5,
        t_half=1.2,
        cv_intra=0.20,
    ),
    "amoxicillin": PKParameters(
        cmax=8000.0,
        auc=25000.0,
        tmax=1.5,
        t_half=1.2,
        cv_intra=0.20,
    ),
    "аторвастатин": PKParameters(
        cmax=27.0,
        auc=150.0,
        tmax=1.0,
        t_half=14.0,
        cv_intra=0.55,
    ),
    "atorvastatin": PKParameters(
        cmax=27.0,
        auc=150.0,
        tmax=1.0,
        t_half=14.0,
        cv_intra=0.55,
    ),
    "диклофенак": PKParameters(
        cmax=2500.0,
        auc=5000.0,
        tmax=2.0,
        t_half=2.0,
        cv_intra=0.30,
    ),
    "diclofenac": PKParameters(
        cmax=2500.0,
        auc=5000.0,
        tmax=2.0,
        t_half=2.0,
        cv_intra=0.30,
    ),
}


def get_pk_parameters(study_input: StudyInput) -> PKParameters:
    """
    Получить PK-параметры для заданного МНН.

    Нормализуем INN (lowercase, strip) и ищем в локальном словаре.
    Если МНН не найден — возвращаем пустой PKParameters (все поля None).
    """
    key = study_input.inn.strip().lower()
    return HARDCODED_PK_DB.get(key, PKParameters())
