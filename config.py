"""
Настройки и константы для прототипа планирования исследований биоэквивалентности.
"""

# Статистические параметры по умолчанию
DEFAULT_ALPHA = 0.05
DEFAULT_POWER = 0.80
DEFAULT_DROPOUT_RATE = 0.20
DEFAULT_SCREEN_FAIL_RATE = 0.20

# Границы биоэквивалентности (отношение T/R)
BE_LOWER = 0.80
BE_UPPER = 1.25

# CV по умолчанию для категорий
CV_LOW_DEFAULT = 0.25
CV_HIGH_DEFAULT = 0.45
CV_UNKNOWN_DEFAULT = 0.25

# Пороги для выбора дизайна
CV_THRESHOLD_REPLICATE_3WAY = 0.30
CV_THRESHOLD_REPLICATE_4WAY = 0.50

# Порог T1/2, при котором предлагается параллельный дизайн (часы)
T_HALF_PARALLEL_THRESHOLD = 48.0

# Минимальный wash-out (дни)
MIN_WASHOUT_DAYS = 7.0

# Поправочные коэффициенты размера выборки для разных дизайнов (эвристика)
DESIGN_ADJUSTMENT = {
    "2x2": 1.0,
    "2x3x3": 1.1,
    "2x4": 1.2,
    "parallel": 1.3,
    "other": 1.0,
}

# LLM настройки
LLM_ENABLED = True  # Включить/выключить использование LLM для генерации синопсиса
LLM_MODEL = "gpt-4"  # Модель OpenAI для использования
LLM_FALLBACK_TO_TEMPLATE = True  # Использовать шаблонную генерацию при ошибке LLM
