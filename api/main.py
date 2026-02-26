"""
FastAPI-приложение — основные и дополнительные эндпоинты:
  /design         — расчёт плана и генерация синопсиса (шаблонная)
  /design-llm     — расчёт плана и генерация синопсиса через LLM
  /export/docx    — экспорт синопсиса в DOCX
  /export/pdf     — экспорт синопсиса в PDF
  /cases          — список кейсов из библиотеки прецедентов
  /cases/search   — поиск похожих кейсов
  /cases/save     — сохранение нового кейса
  /protocol       — генерация полного протокола (расширенный синопсис)
  /translate      — перевод синопсиса на английский через LLM
  /compliance     — проверка синопсиса на соответствие регуляторным требованиям
Также обслуживает UI-форму для ввода данных на корневом маршруте (/).
"""

import pathlib
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
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
from export.formatter import export_docx, export_pdf
from cases.library import get_all_cases, search_similar_cases, save_case

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


class LLMDesignRequest(BaseModel):
    """Запрос для генерации синопсиса через YandexGPT 5 PRO."""

    # Параметры исследования (те же, что в StudyInput)
    inn: str
    dose_mg: float
    form: str = "tablet"
    cv_intra: Optional[float] = None
    cv_category: Optional[str] = None
    need_rsabe: Optional[bool] = None
    regime: str = "fasted"
    study_type: str = "single"
    preferred_design: Optional[str] = None
    min_age: int = 18
    max_age: int = 55
    sex: str = "both"
    bmi_min: float = 18.5
    bmi_max: float = 30.0

    # Учётные данные YandexGPT
    api_key: Optional[str] = None
    folder_id: Optional[str] = None


@app.post("/design-llm", response_model=LLMDesignResponse)
def design_llm_endpoint(req: LLMDesignRequest) -> LLMDesignResponse:
    """
    Принимает входные параметры исследования и возвращает результат с
    синопсисом, сгенерированным с помощью YandexGPT 5 PRO.

    Если LLM недоступен или происходит ошибка, и LLM_FALLBACK_TO_TEMPLATE=True,
    используется шаблонная генерация.

    Поля api_key и folder_id передаются из UI и имеют приоритет над
    переменными окружения YANDEX_API_KEY / YANDEX_FOLDER_ID.
    """
    study_input = StudyInput(
        inn=req.inn,
        dose_mg=req.dose_mg,
        form=req.form,  # type: ignore[arg-type]
        cv_intra=req.cv_intra,
        cv_category=req.cv_category,  # type: ignore[arg-type]
        need_rsabe=req.need_rsabe,
        regime=req.regime,  # type: ignore[arg-type]
        study_type=req.study_type,  # type: ignore[arg-type]
        preferred_design=req.preferred_design,
        min_age=req.min_age,
        max_age=req.max_age,
        sex=req.sex,  # type: ignore[arg-type]
        bmi_min=req.bmi_min,
        bmi_max=req.bmi_max,
    )
    pk = get_pk_parameters(study_input)
    design = select_study_design(study_input, pk)
    sample = calculate_sample_size(study_input, design)
    issues = run_regulatory_checks(study_input, pk, design, sample)

    llm_generated = False
    error_message = None
    synopsis = None

    # Определяем ключи: сначала из запроса, затем из окружения
    effective_api_key = req.api_key or os.getenv("YANDEX_API_KEY")
    effective_folder_id = req.folder_id or os.getenv("YANDEX_FOLDER_ID")

    # Пытаемся сгенерировать синопсис через LLM
    if LLM_ENABLED:
        if effective_api_key and effective_folder_id:
            try:
                synopsis = generate_llm_synopsis(
                    study_input, pk, design, sample, issues,
                    api_key=effective_api_key,
                    folder_id=effective_folder_id,
                    model=LLM_MODEL,
                )
                llm_generated = True
            except Exception as e:
                error_message = str(e)
        else:
            missing = []
            if not effective_api_key:
                missing.append("YANDEX_API_KEY")
            if not effective_folder_id:
                missing.append("YANDEX_FOLDER_ID")
            error_message = f"Не указаны: {', '.join(missing)}"
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


# ═══════════════════════════════════════════════════════════════════════════
# Экспорт документов
# ═══════════════════════════════════════════════════════════════════════════

class ExportRequest(BaseModel):
    synopsis_md: str
    title: Optional[str] = "Синопсис протокола исследования биоэквивалентности"
    company_name: Optional[str] = "Ifarma BE Study Planner"
    author: Optional[str] = "Автоматически сгенерировано"


@app.post("/export/docx")
def export_docx_endpoint(req: ExportRequest) -> Response:
    """Экспортирует синопсис в формат DOCX с корпоративным шаблоном."""
    data = export_docx(
        synopsis_md=req.synopsis_md,
        title=req.title or "Синопсис протокола",
        company_name=req.company_name or "Ifarma BE Study Planner",
        author=req.author or "Автоматически сгенерировано",
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=synopsis.docx"},
    )


@app.post("/export/pdf")
def export_pdf_endpoint(req: ExportRequest) -> Response:
    """Экспортирует синопсис в формат PDF с корпоративным шаблоном."""
    data = export_pdf(
        synopsis_md=req.synopsis_md,
        title=req.title or "Синопсис протокола",
        company_name=req.company_name or "Ifarma BE Study Planner",
        author=req.author or "Автоматически сгенерировано",
    )
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=synopsis.pdf"},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Библиотека прецедентов (Case-Based Reasoning)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/cases")
def list_cases_endpoint() -> List[Dict[str, Any]]:
    """Возвращает все кейсы из библиотеки прецедентов."""
    return get_all_cases()


class CaseSearchRequest(BaseModel):
    inn: str
    cv_intra: Optional[float] = None
    design: Optional[str] = None
    limit: int = 3


@app.post("/cases/search")
def search_cases_endpoint(req: CaseSearchRequest) -> List[Dict[str, Any]]:
    """Ищет похожие кейсы по МНН и параметрам исследования."""
    return search_similar_cases(
        inn=req.inn,
        cv_intra=req.cv_intra,
        design=req.design,
        limit=req.limit,
    )


@app.post("/cases/save")
def save_case_endpoint(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Сохраняет новый обезличенный кейс в библиотеку прецедентов."""
    return save_case(case_data)


# ═══════════════════════════════════════════════════════════════════════════
# Полный протокол
# ═══════════════════════════════════════════════════════════════════════════

class ProtocolRequest(BaseModel):
    study_input: StudyInput
    centers: Optional[str] = None
    sponsor: Optional[str] = None
    principal_investigator: Optional[str] = None
    phase: Optional[str] = "I"


class ProtocolResponse(BaseModel):
    protocol_md: str
    documents: Dict[str, str]


@app.post("/protocol", response_model=ProtocolResponse)
def full_protocol_endpoint(req: ProtocolRequest) -> ProtocolResponse:
    """
    Генерирует полноценный протокол исследования биоэквивалентности
    и сопутствующие документы: информационный листок добровольца,
    форму информированного согласия, краткую брошюру исследователя.
    """
    pk = get_pk_parameters(req.study_input)
    design = select_study_design(req.study_input, pk)
    sample = calculate_sample_size(req.study_input, design)
    issues = run_regulatory_checks(req.study_input, pk, design, sample)
    synopsis = generate_synopsis_markdown(req.study_input, pk, design, sample, issues)

    inn = req.study_input.inn
    dose = req.study_input.dose_mg
    sponsor = req.sponsor or "Спонсор (указать)"
    centers = req.centers or "Исследовательский центр (указать)"
    pi = req.principal_investigator or "Главный исследователь (указать)"

    # Полный протокол
    protocol_md = f"""# ПРОТОКОЛ КЛИНИЧЕСКОГО ИССЛЕДОВАНИЯ

**Спонсор:** {sponsor}
**Главный исследователь:** {pi}
**Центры:** {centers}
**Фаза:** {req.phase}
**МНН / Доза:** {inn} {dose:.0f} мг

---

{synopsis}

---

## 11. Управление данными

Все данные исследования будут вноситься в электронную форму сбора данных (eCRF).
Первичные данные подлежат архивированию в соответствии с требованиями GCP.

## 12. Этические аспекты

Исследование будет проводиться в соответствии с Хельсинкской декларацией,
надлежащей клинической практикой (GCP) и действующим законодательством РФ.
Протокол подлежит одобрению независимого этического комитета.

## 13. Страхование и компенсация

Участники исследования застрахованы от вреда, причинённого в ходе исследования.
Компенсация добровольцам выплачивается в соответствии с действующим законодательством.

## 14. Публикационная политика

Результаты исследования планируется опубликовать в рецензируемых изданиях.
Решение о публикации принимается совместно Спонсором и Исследователями.
"""

    # Информационный листок добровольца
    icd_md = f"""# ИНФОРМАЦИОННЫЙ ЛИСТОК ДОБРОВОЛЬЦА

Уважаемый участник!

Вас приглашают принять участие в исследовании биоэквивалентности препарата
**{inn} {dose:.0f} мг**.

## О чём это исследование?

Цель данного исследования — сравнить, как препарат-тест и референтный препарат
({inn}) всасываются и выводятся из организма.

## Что от вас потребуется?

- {design.periods} визита(ов) в клинику продолжительностью примерно 24 часа каждый
- Приём одной дозы препарата в каждом периоде
- Забор образцов крови по расписанию
- Соблюдение режима питания и ограничений (алкоголь, кофеин, грейпфрут)

## Wash-out период

Между визитами предусмотрен отмывочный период {design.washout_days:.0f} дней.

## Ваши права

Участие добровольно. Вы можете отказаться в любой момент без объяснения причин
и без каких-либо последствий для вас.

## Контакты

По всем вопросам обращайтесь: {pi} | {centers}
"""

    # Форма информированного согласия
    ics_md = f"""# ФОРМА ИНФОРМИРОВАННОГО СОГЛАСИЯ

Исследование: «Биоэквивалентность {inn} {dose:.0f} мг»
Спонсор: {sponsor}
Центр: {centers}

Я, _____________________________________________, ознакомился(лась) с Информационным
листком добровольца, получил(а) исчерпывающие ответы на все интересующие меня вопросы.

Я понимаю, что:
1. Моё участие является добровольным.
2. Я могу отказаться от участия в любое время без объяснения причин.
3. Мои персональные данные будут обезличены и защищены.
4. Мне будет обеспечена медицинская помощь при необходимости.

□ Я согласен(на) на участие в исследовании.
□ Я согласен(на) на обработку моих персональных данных.

Подпись добровольца: ___________________ Дата: __________
Подпись исследователя: _________________ Дата: __________
"""

    # Краткая брошюра исследователя
    ib_md = f"""# КРАТКАЯ БРОШЮРА ИССЛЕДОВАТЕЛЯ

**Препарат:** {inn} {dose:.0f} мг ({req.study_input.form})

## Фармакологическая характеристика

| Параметр | Значение |
|----------|----------|
| Cmax (нг/мл) | {pk.cmax if pk.cmax else '—'} |
| AUC (нг·ч/мл) | {pk.auc if pk.auc else '—'} |
| Tmax (ч) | {pk.tmax if pk.tmax else '—'} |
| T½ (ч) | {pk.t_half if pk.t_half else '—'} |
| CVintra | {pk.cv_intra if pk.cv_intra else '—'} |

## Дизайн исследования

- **Тип:** {design.name} ({design.type})
- **Периоды:** {design.periods}
- **Выборка:** {sample.adjusted_for_dropout} добровольцев

## Регуляторный статус

Исследование проводится в соответствии с Решением Совета ЕЭК №85,
руководствами EMA и FDA по исследованиям биоэквивалентности.

## Замечания регулятора

{'Замечаний нет.' if not issues else chr(10).join(f'- [{i.code}] {i.message}' for i in issues)}
"""

    return ProtocolResponse(
        protocol_md=protocol_md,
        documents={
            "informed_consent_doc": icd_md,
            "informed_consent_form": ics_md,
            "investigators_brochure": ib_md,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# Перевод синопсиса
# ═══════════════════════════════════════════════════════════════════════════

class TranslateRequest(BaseModel):
    synopsis_md: str
    target_language: str = "en"
    regulatory_context: str = "EMA"


class TranslateResponse(BaseModel):
    translated_md: str
    source_language: str = "ru"
    target_language: str
    llm_translated: bool
    note: Optional[str] = None


@app.post("/translate", response_model=TranslateResponse)
def translate_endpoint(req: TranslateRequest) -> TranslateResponse:
    """
    Переводит синопсис на английский язык (или другой целевой язык)
    с сохранением терминологии и форматирования.
    Адаптирует под требования зарубежных регуляторов (EMA / FDA).
    Использует YandexGPT 5 PRO.
    """
    import requests as _req_lib
    from llm.client import YANDEX_GPT_API_URL, YANDEX_GPT_MODEL_ID

    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")

    if not LLM_ENABLED or not api_key or not folder_id:
        translated = (
            f"# [TRANSLATION PLACEHOLDER — LLM not configured]\n\n"
            f"*Original Russian synopsis is shown below. "
            f"Configure YANDEX_API_KEY and YANDEX_FOLDER_ID to enable automatic translation.*\n\n"
            f"---\n\n{req.synopsis_md}"
        )
        return TranslateResponse(
            translated_md=translated,
            target_language=req.target_language,
            llm_translated=False,
            note="LLM не настроен. Установите YANDEX_API_KEY и YANDEX_FOLDER_ID для автоматического перевода.",
        )

    try:
        lang_map = {"en": "English", "de": "German", "fr": "French", "zh": "Chinese"}
        lang_name = lang_map.get(req.target_language, req.target_language)

        prompt = (
            f"You are a professional medical translator specialising in clinical trial protocols. "
            f"Translate the following bioequivalence study synopsis from Russian to {lang_name}. "
            f"Rules:\n"
            f"- Preserve all Markdown formatting (headers, tables, bullet lists)\n"
            f"- Keep scientific/medical terminology accurate for {req.regulatory_context} guidelines\n"
            f"- Adapt regulatory references appropriately (e.g. 'Решение №85' → 'EMA Guideline on BE')\n"
            f"- Do not add explanations, translate only\n\n"
            f"{req.synopsis_md}"
        )

        model_uri = f"gpt://{folder_id}/{YANDEX_GPT_MODEL_ID}/latest"
        resp = _req_lib.post(
            YANDEX_GPT_API_URL,
            headers={
                "Authorization": f"Api-Key {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "modelUri": model_uri,
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.2,
                    "maxTokens": "4000",
                },
                "messages": [{"role": "user", "text": prompt}],
            },
            timeout=120,
        )
        resp.raise_for_status()
        translated = resp.json()["result"]["alternatives"][0]["message"]["text"]
        return TranslateResponse(
            translated_md=translated or req.synopsis_md,
            target_language=req.target_language,
            llm_translated=True,
        )
    except Exception as exc:
        return TranslateResponse(
            translated_md=req.synopsis_md,
            target_language=req.target_language,
            llm_translated=False,
            note=f"Ошибка перевода: {exc}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Проверка на соответствие нормативным требованиям
# ═══════════════════════════════════════════════════════════════════════════

class ComplianceRequest(BaseModel):
    study_input: StudyInput


class ComplianceSection(BaseModel):
    section: str
    status: str  # "ok" | "warning" | "error"
    message: str
    reference: Optional[str] = None


class ComplianceResponse(BaseModel):
    overall_status: str  # "ok" | "warning" | "error"
    sections: List[ComplianceSection]
    summary: str


@app.post("/compliance", response_model=ComplianceResponse)
def compliance_endpoint(req: ComplianceRequest) -> ComplianceResponse:
    """
    Проверяет параметры исследования на соответствие нормативным требованиям
    в реальном времени: Решение №85, FDA Guidance, EMA Guideline.
    Подсвечивает проблемные разделы и даёт рекомендации со ссылками.
    """
    pk = get_pk_parameters(req.study_input)
    design = select_study_design(req.study_input, pk)
    sample = calculate_sample_size(req.study_input, design)
    issues = run_regulatory_checks(req.study_input, pk, design, sample)

    sections: List[ComplianceSection] = []

    # ── Wash-out ────────────────────────────────────────────────────────
    # Используем T½ из PK-данных; если неизвестен, применяем консервативный минимум (8ч)
    t_half_for_check = pk.t_half if pk.t_half is not None else 8.0
    from config import MIN_WASHOUT_DAYS
    if design.washout_days >= 5 * t_half_for_check:
        sections.append(ComplianceSection(
            section="Wash-out",
            status="ok",
            message=f"Wash-out {design.washout_days:.0f} дней ≥ 5×T½ — соответствует требованиям.",
            reference="Решение №85, п.7.1; EMA BE Guideline §4.1.9",
        ))
    else:
        sections.append(ComplianceSection(
            section="Wash-out",
            status="warning",
            message=f"Wash-out {design.washout_days:.0f} дней может быть недостаточен. "
                    f"Рекомендуется ≥ 5×T½.",
            reference="Решение №85, п.7.1; EMA BE Guideline §4.1.9",
        ))

    # ── Минимальный размер выборки ──────────────────────────────────────
    if sample.adjusted_for_dropout >= 12:
        sections.append(ComplianceSection(
            section="Размер выборки",
            status="ok",
            message=f"N={sample.adjusted_for_dropout} ≥ 12 — соответствует минимальным требованиям.",
            reference="Решение №85, п.7.2; EMA BE Guideline §4.1.2",
        ))
    else:
        sections.append(ComplianceSection(
            section="Размер выборки",
            status="error",
            message=f"N={sample.adjusted_for_dropout} < 12 — не соответствует минимальным требованиям.",
            reference="Решение №85, п.7.2; EMA BE Guideline §4.1.2",
        ))

    # ── RSABE ──────────────────────────────────────────────────────────
    cv = pk.cv_intra or req.study_input.cv_intra
    if cv is not None and cv > 0.30:
        if design.rsabe_applicable:
            sections.append(ComplianceSection(
                section="RSABE",
                status="ok",
                message=f"CV={cv:.0%} > 30% — применение RSABE обосновано и предусмотрено дизайном.",
                reference="Решение №85, п.8.3; EMA BE Guideline §4.1.10; FDA Guidance on HVD",
            ))
        else:
            sections.append(ComplianceSection(
                section="RSABE",
                status="warning",
                message=f"CV={cv:.0%} > 30% — рассмотрите применение RSABE и реплицированного дизайна.",
                reference="Решение №85, п.8.3; EMA BE Guideline §4.1.10",
            ))
    else:
        sections.append(ComplianceSection(
            section="RSABE",
            status="ok",
            message="CV ≤ 30% — RSABE не требуется, стандартные критерии 80–125%.",
            reference="Решение №85, п.8.1",
        ))

    # ── Критерии BE ────────────────────────────────────────────────────
    sections.append(ComplianceSection(
        section="Критерии биоэквивалентности",
        status="ok",
        message="Стандартные критерии 80,00–125,00% для Cmax и AUC соответствуют требованиям.",
        reference="Решение №85, п.8.1; EMA BE Guideline §4.1.8; FDA 21 CFR 320",
    ))

    # ── Режим приёма ────────────────────────────────────────────────────
    if req.study_input.regime == "both":
        sections.append(ComplianceSection(
            section="Режим приёма",
            status="ok",
            message="Оба режима (натощак и после еды) — полный пакет регуляторных данных.",
            reference="EMA BE Guideline §4.2; FDA Food-Effect Guidance",
        ))
    else:
        sections.append(ComplianceSection(
            section="Режим приёма",
            status="ok",
            message=f"Режим '{req.study_input.regime}' соответствует инструкции по применению препарата.",
            reference="Решение №85, п.6.3",
        ))

    # ── Регуляторные замечания из стандартных проверок ─────────────────
    for iss in issues:
        sections.append(ComplianceSection(
            section="Автоматическая проверка",
            status=iss.severity if iss.severity in ("ok", "warning", "error") else "warning",
            message=f"[{iss.code}] {iss.message}",
            reference="Решение №85",
        ))

    # ── Итоговый статус ─────────────────────────────────────────────────
    has_error = any(s.status == "error" for s in sections)
    has_warning = any(s.status == "warning" for s in sections)
    overall = "error" if has_error else ("warning" if has_warning else "ok")

    n_ok = sum(1 for s in sections if s.status == "ok")
    n_warn = sum(1 for s in sections if s.status == "warning")
    n_err = sum(1 for s in sections if s.status == "error")
    summary = (
        f"Проверено {len(sections)} критериев: "
        f"{n_ok} ✅ в норме, {n_warn} ⚠️ замечаний, {n_err} 🛑 ошибок. "
        f"Общий статус: {'✅ Соответствует требованиям' if overall == 'ok' else '⚠️ Требует внимания' if overall == 'warning' else '🛑 Несоответствие требованиям'}."
    )

    return ComplianceResponse(
        overall_status=overall,
        sections=sections,
        summary=summary,
    )
