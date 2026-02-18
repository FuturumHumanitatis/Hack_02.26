"""
Генерация синопсиса протокола исследования биоэквивалентности (Markdown).
"""

from typing import List

from models.domain import (
    PKParameters,
    RegulatoryIssue,
    SampleSizeResult,
    StudyDesign,
    StudyInput,
)
from synopsis.templates import (
    BIOANALYTICAL_METHOD_TPL,
    EXCLUSION_CRITERIA_TPL,
    INCLUSION_CRITERIA_TPL,
    SAFETY_MONITORING_TPL,
)


def _regime_label(regime: str) -> str:
    mapping = {"fasted": "натощак", "fed": "после еды", "both": "натощак и после еды"}
    return mapping.get(regime, regime)


def _sex_label(sex: str) -> str:
    mapping = {"male": "мужской", "female": "женский", "both": "мужской и женский"}
    return mapping.get(sex, sex)


def _severity_icon(severity: str) -> str:
    return {"info": "ℹ️", "warning": "⚠️", "error": "🛑"}.get(severity, "•")


def generate_synopsis_markdown(
    study_input: StudyInput,
    pk: PKParameters,
    design: StudyDesign,
    sample_size: SampleSizeResult,
    issues: List[RegulatoryIssue],
) -> str:
    """Собирает полный Markdown-документ синопсиса протокола."""

    sections: List[str] = []

    # ── 1. Название ──
    title = (
        f"# Синопсис протокола: исследование биоэквивалентности "
        f"{study_input.inn} {study_input.dose_mg:.0f} мг"
    )
    sections.append(title)

    # ── 2. Цели ──
    sections.append("## 1. Цели исследования")
    sections.append(
        f"**Основная цель:** оценить биоэквивалентность тестового препарата "
        f"({study_input.inn}, {study_input.dose_mg:.0f} мг, {study_input.form}) "
        f"и референтного препарата по параметрам Cmax и AUC.\n\n"
        f"**Дополнительная цель:** оценить безопасность и переносимость "
        f"однократного приёма тестового и референтного препаратов."
    )

    # ── 3. Задачи ──
    sections.append("## 2. Задачи исследования")
    tasks = [
        f"Определить концентрации {study_input.inn} в плазме крови после однократного "
        f"приёма тестового и референтного препаратов.",
        "Рассчитать фармакокинетические параметры: Cmax, AUC₀₋t, AUC₀₋∞, Tmax, T½.",
        "Оценить биоэквивалентность на основании 90 % доверительных интервалов "
        "для отношения T/R параметров Cmax и AUC.",
        "Оценить безопасность и переносимость препаратов по данным мониторинга "
        "нежелательных явлений, жизненных показателей и лабораторных анализов.",
    ]
    sections.append("\n".join(f"- {t}" for t in tasks))

    # ── 4. Дизайн ──
    sections.append("## 3. Дизайн исследования")
    seq_str = ", ".join(design.sequences)
    sections.append(
        f"- **Тип дизайна:** {design.name} ({design.type})\n"
        f"- **Периоды:** {design.periods}\n"
        f"- **Последовательности:** {seq_str}\n"
        f"- **Wash-out:** {design.washout_days:.0f} дней\n"
        f"- **Режим приёма:** {_regime_label(study_input.regime)}\n"
        f"- **RSABE:** {'да' if design.rsabe_applicable else 'нет'}"
    )

    # ── 5. Популяция и критерии ──
    sections.append("## 4. Популяция и критерии отбора")
    sections.append(
        f"В исследование планируется включить здоровых добровольцев "
        f"({_sex_label(study_input.sex)} пол) в возрасте от "
        f"{study_input.min_age} до {study_input.max_age} лет."
    )

    sections.append("### 4.1 Критерии включения")
    inc = [
        c.format(
            min_age=study_input.min_age,
            max_age=study_input.max_age,
            bmi_min=study_input.bmi_min,
            bmi_max=study_input.bmi_max,
        )
        for c in INCLUSION_CRITERIA_TPL
    ]
    sections.append("\n".join(f"{i+1}. {c}" for i, c in enumerate(inc)))

    sections.append("### 4.2 Критерии исключения")
    sections.append(
        "\n".join(f"{i+1}. {c}" for i, c in enumerate(EXCLUSION_CRITERIA_TPL))
    )

    # ── 6. PK-параметры ──
    sections.append("## 5. Фармакокинетические параметры референтного препарата")
    sections.append(
        "| Параметр | Значение |\n"
        "|----------|----------|\n"
        f"| Cmax (нг/мл) | {pk.cmax if pk.cmax is not None else '—'} |\n"
        f"| AUC (нг·ч/мл) | {pk.auc if pk.auc is not None else '—'} |\n"
        f"| Tmax (ч) | {pk.tmax if pk.tmax is not None else '—'} |\n"
        f"| T½ (ч) | {pk.t_half if pk.t_half is not None else '—'} |\n"
        f"| CVintra | {pk.cv_intra if pk.cv_intra is not None else '—'} |"
    )

    # ── 7. Статистика ──
    sections.append("## 6. Статистическая методология")
    sections.append(
        "Первичный фармакокинетический анализ будет проведён на "
        "лог-трансформированных значениях Cmax и AUC₀₋t с использованием "
        "дисперсионного анализа (ANOVA) для перекрёстного дизайна.\n\n"
        "Биоэквивалентность будет установлена, если 90 % доверительный интервал "
        "для геометрического отношения средних (тестовый / референтный) "
        "для каждого параметра попадает в диапазон **80,00 – 125,00 %**."
    )

    # ── 8. Безопасность ──
    sections.append("## 7. План мониторинга безопасности")
    sections.append(SAFETY_MONITORING_TPL)

    # ── 9. Биоаналитический метод ──
    sections.append("## 8. Биоаналитический метод")
    sections.append(BIOANALYTICAL_METHOD_TPL)

    # ── 10. Размер выборки ──
    sections.append("## 9. Расчёт размера выборки")
    sections.append(
        f"- **Базовый N:** {sample_size.base_n}\n"
        f"- **N с учётом потерь (drop-out {sample_size.dropout_rate:.0%}, "
        f"screen-fail {sample_size.screen_fail_rate:.0%}):** "
        f"{sample_size.adjusted_for_dropout}"
    )

    # ── 11. Замечания ──
    sections.append("## 10. Автоматические замечания")
    if issues:
        for iss in issues:
            icon = _severity_icon(iss.severity)
            sections.append(f"- {icon} **[{iss.code}]** ({iss.severity}): {iss.message}")
    else:
        sections.append("Замечаний нет.")

    return "\n\n".join(sections) + "\n"
