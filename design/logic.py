"""
Логика выбора дизайна исследования биоэквивалентности.
"""

import config
from models.domain import PKParameters, StudyDesign, StudyInput


def _effective_cv(study_input: StudyInput, pk: PKParameters) -> float:
    """Определяет эффективный CVintra для выбора дизайна."""
    # 1. Пользовательское числовое значение
    if study_input.cv_intra is not None:
        return study_input.cv_intra
    # 2. Значение из PK-базы
    if pk.cv_intra is not None:
        return pk.cv_intra
    # 3. Категория пользователя
    if study_input.cv_category == "low":
        return config.CV_LOW_DEFAULT
    if study_input.cv_category == "high":
        return config.CV_HIGH_DEFAULT
    # 4. Умолчание
    return config.CV_UNKNOWN_DEFAULT


def _washout_days(pk: PKParameters) -> float:
    """Расчёт wash-out: ≥ 5 × T1/2, но не менее MIN_WASHOUT_DAYS."""
    if pk.t_half is not None:
        return max(5.0 * pk.t_half / 24.0, config.MIN_WASHOUT_DAYS)
    return config.MIN_WASHOUT_DAYS


def select_study_design(
    study_input: StudyInput, pk: PKParameters
) -> StudyDesign:
    """
    Выбирает дизайн исследования на основе CVintra, T1/2 и предпочтений.

    Правила (для прототипа):
    - CV ≤ 0.30 → стандартный 2×2 cross-over
    - 0.30 < CV ≤ 0.50 → 3-way replicate (2×3×3)
    - CV > 0.50 → 4-way replicate (2×4)
    - T1/2 > 48 ч → параллельный дизайн
    - Пользовательское предпочтение переопределяет автовыбор.
    """
    cv = _effective_cv(study_input, pk)
    washout = _washout_days(pk)
    rsabe = cv > config.CV_THRESHOLD_REPLICATE_3WAY

    # Длинный T1/2 → параллельный дизайн
    if pk.t_half is not None and pk.t_half > config.T_HALF_PARALLEL_THRESHOLD:
        design = StudyDesign(
            name="Параллельный дизайн (длинный T1/2)",
            type="parallel",
            periods=1,
            sequences=["T", "R"],
            washout_days=0,
            rsabe_applicable=rsabe,
        )
    elif cv <= config.CV_THRESHOLD_REPLICATE_3WAY:
        design = StudyDesign(
            name="Стандартный 2×2 перекрёстный дизайн",
            type="2x2",
            periods=2,
            sequences=["TR", "RT"],
            washout_days=washout,
            rsabe_applicable=False,
        )
    elif cv <= config.CV_THRESHOLD_REPLICATE_4WAY:
        design = StudyDesign(
            name="Реплицированный 3-периодный дизайн (2×3×3)",
            type="2x3x3",
            periods=3,
            sequences=["TRR", "RRT"],
            washout_days=washout,
            rsabe_applicable=True,
        )
    else:
        design = StudyDesign(
            name="Реплицированный 4-периодный дизайн (2×4)",
            type="2x4",
            periods=4,
            sequences=["TRTR", "RTRT"],
            washout_days=washout,
            rsabe_applicable=True,
        )

    # Если пользователь задал предпочтительный дизайн — переопределяем имя,
    # но оставляем расчётные параметры (rsabe, washout и пр.)
    if study_input.preferred_design:
        design = design.model_copy(
            update={"name": f"Пользовательский: {study_input.preferred_design}"}
        )

    return design
