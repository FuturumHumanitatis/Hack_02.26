"""
FastAPI-приложение — единственный POST-эндпоинт /design,
который принимает параметры исследования и возвращает полный результат.
"""

from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from design.logic import select_study_design
from models.domain import (
    PKParameters,
    RegulatoryIssue,
    SampleSizeResult,
    StudyDesign,
    StudyInput,
)
from pk_data.source import get_pk_parameters
from reg.checks import run_regulatory_checks
from stats.sample_size import calculate_sample_size
from synopsis.generator import generate_synopsis_markdown

app = FastAPI(
    title="Ifarma BE Study Planner",
    description="Прототип AI-инструмента для планирования исследований биоэквивалентности",
    version="0.1.0",
)


class DesignResponse(BaseModel):
    pk: PKParameters
    design: StudyDesign
    sample_size: SampleSizeResult
    issues: List[RegulatoryIssue]
    synopsis_md: str


@app.post("/design", response_model=DesignResponse)
def design_endpoint(study_input: StudyInput) -> DesignResponse:
    """
    Принимает входные параметры исследования и возвращает:
    - PK-параметры референтного препарата,
    - выбранный дизайн,
    - расчёт размера выборки,
    - список регуляторных замечаний,
    - текст синопсиса (Markdown).
    """
    pk = get_pk_parameters(study_input)
    design = select_study_design(study_input, pk)
    sample = calculate_sample_size(study_input, design)
    issues = run_regulatory_checks(study_input, pk, design, sample)
    synopsis = generate_synopsis_markdown(study_input, pk, design, sample, issues)

    return DesignResponse(
        pk=pk,
        design=design,
        sample_size=sample,
        issues=issues,
        synopsis_md=synopsis,
    )
