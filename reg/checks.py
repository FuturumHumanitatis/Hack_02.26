"""
Регуляторные проверки для протокола исследования биоэквивалентности.

Простые if-правила, основанные на Решении № 85 ЕАЭС и базовых принципах GCP.
"""

from typing import List

import config
from models.domain import (
    PKParameters,
    RegulatoryIssue,
    SampleSizeResult,
    StudyDesign,
    StudyInput,
)


def _effective_cv(study_input: StudyInput, pk: PKParameters) -> float:
    if study_input.cv_intra is not None:
        return study_input.cv_intra
    if pk.cv_intra is not None:
        return pk.cv_intra
    if study_input.cv_category == "low":
        return config.CV_LOW_DEFAULT
    if study_input.cv_category == "high":
        return config.CV_HIGH_DEFAULT
    return config.CV_UNKNOWN_DEFAULT


def run_regulatory_checks(
    study_input: StudyInput,
    pk: PKParameters,
    design: StudyDesign,
    sample_size: SampleSizeResult,
) -> List[RegulatoryIssue]:
    """
    Выполняет набор регуляторных проверок и возвращает список замечаний.
    """
    issues: List[RegulatoryIssue] = []

    # 1. Несоответствие числа периодов типу дизайна
    if design.type in {"2x2", "2x3x3", "2x4"} and design.periods < 2:
        issues.append(
            RegulatoryIssue(
                code="PERIODS_INCONSISTENT",
                severity="error",
                message=(
                    f"Тип дизайна «{design.type}» предполагает ≥ 2 периодов, "
                    f"но указано {design.periods}."
                ),
            )
        )

    # 2. Wash-out слишком короткий
    if design.type != "parallel" and pk.t_half is not None:
        min_washout = 5.0 * pk.t_half / 24.0  # дни
        if design.washout_days < min_washout:
            issues.append(
                RegulatoryIssue(
                    code="WASHOUT_TOO_SHORT",
                    severity="warning",
                    message=(
                        f"Wash-out ({design.washout_days:.1f} дн.) короче рекомендуемых "
                        f"5 × T1/2 ({min_washout:.1f} дн.)."
                    ),
                )
            )

    # 3. Маленький размер выборки
    if sample_size.base_n < 12:
        issues.append(
            RegulatoryIssue(
                code="LOW_SAMPLE_SIZE",
                severity="warning",
                message=(
                    f"Базовый размер выборки ({sample_size.base_n}) "
                    "меньше рекомендуемого минимума 12 добровольцев."
                ),
            )
        )

    # 4. Режим «оба» при 2-периодном дизайне
    if study_input.regime == "both" and design.periods == 2:
        issues.append(
            RegulatoryIssue(
                code="FASTED_FED_SPLIT",
                severity="info",
                message=(
                    "Исследования натощак и после еды обычно проводятся "
                    "как два отдельных исследования."
                ),
            )
        )

    # 5. RSABE может быть уместен
    cv = _effective_cv(study_input, pk)
    if not design.rsabe_applicable and cv > config.CV_THRESHOLD_REPLICATE_3WAY:
        issues.append(
            RegulatoryIssue(
                code="RSABE_MAY_BE_CONSIDERED",
                severity="info",
                message=(
                    f"CVintra ({cv:.2f}) > {config.CV_THRESHOLD_REPLICATE_3WAY}. "
                    "Рекомендуется рассмотреть RSABE и реплицированный дизайн."
                ),
            )
        )

    # 6. Высокий drop-out rate
    if sample_size.dropout_rate > 0.3:
        issues.append(
            RegulatoryIssue(
                code="HIGH_DROPOUT",
                severity="warning",
                message=(
                    f"Уровень drop-out ({sample_size.dropout_rate:.0%}) "
                    "превышает типичные 20–25 %. Убедитесь в обоснованности."
                ),
            )
        )

    # 7. Длительный wash-out (> 28 дней) — может быть неудобно для добровольцев
    if design.washout_days > 28:
        issues.append(
            RegulatoryIssue(
                code="LONG_WASHOUT",
                severity="info",
                message=(
                    f"Wash-out ({design.washout_days:.0f} дн.) превышает 28 дней. "
                    "Рассмотрите параллельный дизайн."
                ),
            )
        )

    return issues
