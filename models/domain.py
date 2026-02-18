"""
Доменные модели для прототипа планирования исследований биоэквивалентности.
Используем Pydantic v2 BaseModel для валидации и сериализации.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class StudyInput(BaseModel):
    """Входные параметры исследования, задаваемые пользователем."""

    inn: str = Field(..., description="МНН (INN) действующего вещества")
    dose_mg: float = Field(..., gt=0, description="Дозировка, мг")
    form: Literal["tablet", "capsule", "solution", "other"] = Field(
        "tablet", description="Лекарственная форма"
    )

    # Внутрисубъектная вариабельность: число 0‑1 (доля) или категория
    cv_intra: Optional[float] = Field(
        None, ge=0, le=1, description="CVintra как доля (0–1)"
    )
    cv_category: Optional[Literal["low", "high"]] = Field(
        None, description="Категория CVintra, если число не задано"
    )

    need_rsabe: Optional[bool] = Field(
        None, description="Необходимость применения RSABE"
    )
    regime: Literal["fasted", "fed", "both"] = Field(
        "fasted", description="Режим приёма (натощак / после еды / оба)"
    )
    study_type: Literal["single", "two_stage"] = Field(
        "single", description="Тип исследования (однофазное / двухфазное)"
    )
    preferred_design: Optional[str] = Field(
        None, description="Предпочтительный дизайн (если есть)"
    )

    # Параметры популяции
    min_age: int = Field(18, ge=18, description="Минимальный возраст добровольцев")
    max_age: int = Field(55, le=65, description="Максимальный возраст добровольцев")
    sex: Literal["male", "female", "both"] = Field(
        "both", description="Пол добровольцев"
    )
    bmi_min: float = Field(18.5, description="Минимальный ИМТ")
    bmi_max: float = Field(30.0, description="Максимальный ИМТ")


class PKParameters(BaseModel):
    """Фармакокинетические параметры референтного препарата."""

    cmax: Optional[float] = Field(None, description="Cmax (нг/мл)")
    auc: Optional[float] = Field(None, description="AUC (нг·ч/мл)")
    tmax: Optional[float] = Field(None, description="Tmax (ч)")
    t_half: Optional[float] = Field(None, description="T1/2 (ч)")
    cv_intra: Optional[float] = Field(
        None, ge=0, le=1, description="CVintra для данного препарата (доля 0–1)"
    )


class StudyDesign(BaseModel):
    """Описание выбранного дизайна исследования."""

    name: str = Field(..., description="Название дизайна")
    type: Literal["2x2", "2x3x3", "2x4", "parallel", "other"] = Field(
        ..., description="Тип дизайна"
    )
    periods: int = Field(..., ge=1, description="Количество периодов")
    sequences: List[str] = Field(
        ..., description="Последовательности (напр. ['TR','RT'])"
    )
    washout_days: float = Field(..., ge=0, description="Wash-out между периодами (дни)")
    rsabe_applicable: bool = Field(
        False, description="Применимость RSABE для данного дизайна/CV"
    )


class SampleSizeResult(BaseModel):
    """Результат расчёта размера выборки."""

    base_n: int = Field(..., ge=1, description="Базовый N (без поправок)")
    adjusted_for_dropout: int = Field(
        ..., ge=1, description="N с учётом drop-out и screen-fail"
    )
    dropout_rate: float = Field(..., ge=0, le=1)
    screen_fail_rate: float = Field(..., ge=0, le=1)


class RegulatoryIssue(BaseModel):
    """Одно регуляторное замечание."""

    code: str = Field(..., description="Код замечания")
    severity: Literal["info", "warning", "error"] = Field(
        ..., description="Уровень серьёзности"
    )
    message: str = Field(..., description="Описание замечания")
