# strategy_menu/constants.py

"""
Константы для системы стратегий Zapret
"""

# Метки для стратегий
LABEL_RECOMMENDED = "recommended"
LABEL_CAUTION = "caution"
LABEL_EXPERIMENTAL = "experimental"
LABEL_STABLE = "stable"
LABEL_WARP = "warp"

# Константы для скрытого запуска
SW_HIDE = 0
CREATE_NO_WINDOW = 0x08000000
STARTF_USESHOWWINDOW = 0x00000001

# Настройки отображения меток
LABEL_COLORS = {
    LABEL_RECOMMENDED: "#00B900",  # Зеленый для рекомендуемых
    LABEL_CAUTION: "#FF6600",      # Оранжевый для стратегий с осторожностью
    LABEL_EXPERIMENTAL: "#CC0000", # Красный для экспериментальных
    LABEL_STABLE: "#006DDA",       # Синий для стабильных
    LABEL_WARP: "#EE850C"          # Оранжевый для WARP
}

LABEL_TEXTS = {
    LABEL_RECOMMENDED: "РЕКОМЕНДУЕМ",
    LABEL_CAUTION: "С ОСТОРОЖНОСТЬЮ",
    LABEL_EXPERIMENTAL: "ЭКСПЕРИМЕНТАЛЬНАЯ",
    LABEL_STABLE: "СТАБИЛЬНАЯ",
    LABEL_WARP: "WARP"
}

MINIMUM_WIDTH_STRAG = 800  # Увеличиваем ширину для таблицы
MINIMUM_WIDTH = 900  # Уменьшаем минимальную ширину основного окна
MINIMIM_HEIGHT = 650  # Минимальная высота окна