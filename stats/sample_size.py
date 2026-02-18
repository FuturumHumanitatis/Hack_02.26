"""
Расчёт размера выборки для исследования биоэквивалентности.

Для 2×2 cross-over используется нормальное приближение TOST
на лог-трансформированных данных.
Для других дизайнов — эвристические поправочные коэффициенты (прототип).
"""

import math
from typing import Optional

import config
from models.domain import SampleSizeResult, StudyDesign, StudyInput


def estimate_log_variance_from_cv(cv_intra: float) -> float:
    """
    Оценка дисперсии лог-трансформированных данных по CVintra.

    CV задаётся как доля (0.25, а не 25%).
    sigma² = ln(1 + CV²)
    """
    return math.log(1.0 + cv_intra ** 2)


def _z(alpha: float) -> float:
    """Квантиль стандартного нормального распределения (приближение)."""
    # Используем обратную функцию ошибок через приближение Абрамовица—Стегуна.
    # Для p = 1 - alpha:
    p = 1.0 - alpha
    # Rational approximation (Abramowitz & Stegun 26.2.23)
    if p <= 0.0 or p >= 1.0:
        return 0.0
    if p < 0.5:
        sign = -1.0
        pp = p
    else:
        sign = 1.0
        pp = 1.0 - p
    t = math.sqrt(-2.0 * math.log(pp))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    z = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)
    return sign * z


def _base_n_2x2(
    sigma2: float,
    alpha: float,
    power: float,
    theta_lower: float,
    theta_upper: float,
) -> int:
    """
    Базовый расчёт N для 2×2 cross-over (TOST, нормальное приближение).

    Формула (на одну группу):
        n_per_seq = 2 * sigma² * (z_{1-alpha} + z_{power})² / (ln(theta_upper))²

    Общий N = 2 * n_per_seq (две последовательности).

    Допущения:
    - Истинное отношение T/R = 1.0 (worst case: середина диапазона).
    - Одностороннее alpha для каждой границы TOST.
    """
    z_alpha = _z(1.0 - alpha)      # e.g. alpha=0.05 → z=1.645
    z_power = _z(power)             # e.g. power=0.80 → z=0.842

    # Используем симметричную границу ln(theta_upper)
    log_margin = math.log(theta_upper)

    n_per_seq = 2.0 * sigma2 * (z_alpha + z_power) ** 2 / (log_margin ** 2)
    n_per_seq = math.ceil(n_per_seq)
    # Минимум 6 на группу
    n_per_seq = max(n_per_seq, 6)
    base_n = 2 * n_per_seq
    return base_n


def calculate_sample_size(
    study_input: StudyInput,
    design: StudyDesign,
    alpha: float = config.DEFAULT_ALPHA,
    power: float = config.DEFAULT_POWER,
    theta_lower: float = config.BE_LOWER,
    theta_upper: float = config.BE_UPPER,
    dropout_rate: float = config.DEFAULT_DROPOUT_RATE,
    screen_fail_rate: float = config.DEFAULT_SCREEN_FAIL_RATE,
) -> SampleSizeResult:
    """
    Рассчитать размер выборки с учётом дизайна, CV, мощности и потерь.

    Шаги:
    1. Определить эффективный CV.
    2. Рассчитать sigma² = ln(1 + CV²).
    3. Получить базовый N для 2×2 cross-over.
    4. Скорректировать N поправочным коэффициентом дизайна.
    5. Добавить поправку на drop-out и screen-fail.
    """
    # Эффективный CV
    cv: Optional[float] = study_input.cv_intra
    if cv is None:
        if study_input.cv_category == "low":
            cv = config.CV_LOW_DEFAULT
        elif study_input.cv_category == "high":
            cv = config.CV_HIGH_DEFAULT
        else:
            cv = config.CV_UNKNOWN_DEFAULT

    sigma2 = estimate_log_variance_from_cv(cv)

    # Базовый N (как если бы 2×2)
    raw_n = _base_n_2x2(sigma2, alpha, power, theta_lower, theta_upper)

    # Поправка на тип дизайна
    adj_factor = config.DESIGN_ADJUSTMENT.get(design.type, 1.0)
    base_n = math.ceil(raw_n * adj_factor)
    # Убедимся, что N чётное (для балансировки последовательностей)
    if base_n % 2 != 0:
        base_n += 1

    # Поправка на потери
    retention = (1.0 - dropout_rate) * (1.0 - screen_fail_rate)
    adjusted = math.ceil(base_n / retention) if retention > 0 else base_n
    if adjusted % 2 != 0:
        adjusted += 1

    return SampleSizeResult(
        base_n=base_n,
        adjusted_for_dropout=adjusted,
        dropout_rate=dropout_rate,
        screen_fail_rate=screen_fail_rate,
    )
