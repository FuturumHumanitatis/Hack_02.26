"""
FastAPI-приложение — единственный POST-эндпоинт /design,
который принимает параметры исследования и возвращает полный результат.
Также обслуживает UI-форму для ввода данных на корневом маршруте (/).
"""

import pathlib
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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
from llm.client import generate_llm_synopsis
from config import LLM_ENABLED, LLM_MODEL, LLM_FALLBACK_TO_TEMPLATE

_STATIC_DIR = pathlib.Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="Ifarma BE Study Planner",
    description="Прототип AI-инструмента для планирования исследований биоэквивалентности",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse)
def ui_form() -> HTMLResponse:
    """Отдаёт HTML-форму для ввода параметров исследования."""
    html_path = _STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


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


class LLMDesignResponse(BaseModel):
    pk: PKParameters
    design: StudyDesign
    sample_size: SampleSizeResult
    issues: List[RegulatoryIssue]
    synopsis_md: str
    llm_generated: bool
    error_message: Optional[str] = None


@app.post("/design-llm", response_model=LLMDesignResponse)
def design_llm_endpoint(study_input: StudyInput) -> LLMDesignResponse:
    """
    Принимает входные параметры исследования и возвращает результат с 
    синопсисом, сгенерированным с помощью LLM (GPT-4).
    
    Если LLM недоступен или происходит ошибка, и LLM_FALLBACK_TO_TEMPLATE=True,
    используется шаблонная генерация.
    """
    pk = get_pk_parameters(study_input)
    design = select_study_design(study_input, pk)
    sample = calculate_sample_size(study_input, design)
    issues = run_regulatory_checks(study_input, pk, design, sample)
    
    llm_generated = False
    error_message = None
    synopsis = None
    
    # Пытаемся сгенерировать синопсис через LLM
    if LLM_ENABLED:
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                synopsis = generate_llm_synopsis(
                    study_input, pk, design, sample, issues,
                    api_key=api_key,
                    model=LLM_MODEL
                )
                llm_generated = True
            else:
                error_message = "OPENAI_API_KEY не установлен"
        except Exception as e:
            error_message = str(e)
    else:
        error_message = "LLM отключен в конфигурации"
    
    # Fallback к шаблонной генерации
    if synopsis is None:
        if LLM_FALLBACK_TO_TEMPLATE:
            synopsis = generate_synopsis_markdown(study_input, pk, design, sample, issues)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Не удалось сгенерировать синопсис через LLM: {error_message}"
            )
    
    return LLMDesignResponse(
        pk=pk,
        design=design,
        sample_size=sample,
        issues=issues,
        synopsis_md=synopsis,
        llm_generated=llm_generated,
        error_message=error_message if not llm_generated else None,
    )
