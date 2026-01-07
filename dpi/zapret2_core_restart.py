"""
dpi/zapret2_core_restart.py - Унифицированный механизм перезапуска DPI для режима direct_zapret2

Этот модуль предоставляет единый API для перезагрузки DPI сервиса когда настройки
изменяются в UI (syndata, filter_mode, out_range и т.д.).

Использование:
    from dpi.zapret2_core_restart import trigger_dpi_reload, DPIReloadDebouncer

    # Немедленный перезапуск (для редких действий)
    trigger_dpi_reload(app, reason="filter_mode_changed", category_key="youtube")

    # С debounce (для частых изменений, например SpinBox)
    debouncer = DPIReloadDebouncer(app)
    debouncer.schedule_reload(reason="syndata_changed", category_key="youtube")
"""

from typing import Optional, TYPE_CHECKING
from PyQt6.QtCore import QTimer

if TYPE_CHECKING:
    from main import LupiDPIApp

from log import log


def _is_direct_zapret2_mode() -> bool:
    """
    Проверяет что текущий режим запуска = direct_zapret2.

    Returns:
        True если режим direct_zapret2, False для других режимов
    """
    try:
        from strategy_menu import get_strategy_launch_method
        method = get_strategy_launch_method()
        return method == "direct_zapret2"
    except Exception as e:
        log(f"Ошибка проверки режима запуска: {e}", "ERROR")
        return False


def _is_dpi_running(app: 'LupiDPIApp') -> bool:
    """
    Проверяет запущен ли DPI процесс.

    Args:
        app: Ссылка на главное приложение

    Returns:
        True если winws/winws2 процесс запущен
    """
    try:
        if hasattr(app, 'dpi_starter') and app.dpi_starter:
            return app.dpi_starter.check_process_running_wmi(silent=True)
        return False
    except Exception as e:
        log(f"Ошибка проверки состояния DPI: {e}", "DEBUG")
        return False


def _has_active_strategies() -> bool:
    """
    Проверяет есть ли активные стратегии (не все = 'none').

    Returns:
        True если есть хотя бы одна активная стратегия
    """
    try:
        from strategy_menu import get_direct_strategy_selections
        selections = get_direct_strategy_selections()
        return any(sid and sid != 'none' for sid in selections.values())
    except Exception as e:
        log(f"Ошибка проверки активных стратегий: {e}", "ERROR")
        return False


def trigger_dpi_reload(
    app: 'LupiDPIApp',
    reason: str,
    category_key: Optional[str] = None,
) -> bool:
    """
    Унифицированный механизм перезагрузки DPI для режима direct_zapret2.

    Выполняет:
    1. Проверяет что текущий режим = direct_zapret2
    2. Вызывает regenerate_preset_file() для обновления preset-zapret2.txt
    3. Проверяет запущен ли DPI через app.dpi_starter.check_process_running_wmi()
    4. Если запущен - перезапускает через app.dpi_controller.start_dpi_async()

    Args:
        app: Главное приложение (LupiDPIApp)
        reason: Причина перезагрузки для логирования:
            - "syndata_changed" - изменились настройки syndata
            - "filter_mode_changed" - изменился режим фильтрации
            - "strategy_changed" - изменилась выбранная стратегия
            - "send_changed" - изменились настройки send
            - "out_range_changed" - изменился out_range
        category_key: Опциональная категория которая изменилась

    Returns:
        bool: True если перезапуск запущен, False если DPI не запущен или режим не direct_zapret2
    """
    # 1. Проверяем режим
    if not _is_direct_zapret2_mode():
        log(f"trigger_dpi_reload пропущен: режим не direct_zapret2", "DEBUG")
        return False

    # 2. Проверяем наличие dpi_controller
    if not hasattr(app, 'dpi_controller') or not app.dpi_controller:
        log("trigger_dpi_reload: dpi_controller не найден", "DEBUG")
        return False

    # 3. Регенерируем preset файл
    try:
        from strategy_menu import regenerate_preset_file
        regenerate_preset_file()
        log(f"Preset файл обновлен (причина: {reason})", "DEBUG")
    except Exception as e:
        log(f"Ошибка регенерации preset файла: {e}", "ERROR")
        # Продолжаем - возможно preset уже актуален

    # 4. Проверяем запущен ли DPI
    if not _is_dpi_running(app):
        log(f"trigger_dpi_reload: DPI не запущен, перезапуск не требуется", "DEBUG")
        return False

    # 5. Проверяем есть ли активные стратегии
    if not _has_active_strategies():
        log("Нет активных стратегий - останавливаем DPI", "INFO")
        app.dpi_controller.stop_dpi_async()
        return True

    # 6. Комбинируем стратегии и перезапускаем
    try:
        from strategy_menu import get_direct_strategy_selections, combine_strategies

        selections = get_direct_strategy_selections()
        combined = combine_strategies(**selections)

        combined_data = {
            'id': 'DIRECT_MODE',
            'name': 'Прямой запуск (Запрет 2)',
            'is_combined': True,
            'args': combined['args'],
            'selections': selections.copy()
        }

        category_info = f" [{category_key}]" if category_key else ""
        log(f"Перезапуск DPI{category_info} (причина: {reason})", "INFO")

        app.dpi_controller.start_dpi_async(selected_mode=combined_data)
        return True

    except Exception as e:
        log(f"Ошибка перезапуска DPI: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


class DPIReloadDebouncer:
    """
    Debounce механизм для предотвращения частых перезапусков DPI.

    Используется когда пользователь быстро меняет значения SpinBox или других
    частоизменяемых контролов. Вместо перезапуска DPI на каждое изменение,
    ждем пока пользователь закончит редактирование.

    Интервал по умолчанию: 500ms

    Пример использования:
        class MyPage(BasePage):
            def __init__(self, parent=None):
                super().__init__(parent)
                self._debouncer = None

            def _ensure_debouncer(self):
                if self._debouncer is None and self.parent_app:
                    self._debouncer = DPIReloadDebouncer(self.parent_app)

            def _on_spinbox_changed(self, value: int):
                # ... сохранение в реестр ...
                self._ensure_debouncer()
                if self._debouncer:
                    self._debouncer.schedule_reload(
                        reason="value_changed",
                        category_key=self._category_key
                    )
    """

    def __init__(self, app: 'LupiDPIApp', delay_ms: int = 500):
        """
        Инициализирует debouncer.

        Args:
            app: Ссылка на главное приложение (LupiDPIApp)
            delay_ms: Задержка в миллисекундах (по умолчанию 500ms)
        """
        self._app = app
        self._delay_ms = delay_ms
        self._timer: Optional[QTimer] = None
        self._pending_reason: Optional[str] = None
        self._pending_category: Optional[str] = None

    def schedule_reload(self, reason: str, category_key: Optional[str] = None):
        """
        Планирует перезагрузку DPI с debounce.

        Если вызвать несколько раз за delay_ms миллисекунд - выполнится только
        последний вызов. Это предотвращает спам перезапусков когда пользователь
        быстро крутит SpinBox.

        Args:
            reason: Причина перезагрузки для логирования
            category_key: Опциональная категория которая изменилась
        """
        # Сохраняем параметры последнего вызова
        self._pending_reason = reason
        self._pending_category = category_key

        # Создаем таймер если его нет
        if self._timer is None:
            self._timer = QTimer()
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._on_timer_expired)

        # Перезапускаем таймер (это и есть debounce)
        self._timer.stop()
        self._timer.start(self._delay_ms)

        log(f"DPI reload запланирован через {self._delay_ms}ms (причина: {reason})", "DEBUG")

    def _on_timer_expired(self):
        """Вызывается когда таймер истек - выполняем reload"""
        if self._pending_reason:
            trigger_dpi_reload(
                self._app,
                reason=self._pending_reason,
                category_key=self._pending_category
            )

        # Очищаем pending состояние
        self._pending_reason = None
        self._pending_category = None

    def cancel(self):
        """Отменяет запланированный reload"""
        if self._timer:
            self._timer.stop()
        self._pending_reason = None
        self._pending_category = None

    def flush(self):
        """Немедленно выполняет запланированный reload (без ожидания таймера)"""
        if self._timer:
            self._timer.stop()
        if self._pending_reason:
            self._on_timer_expired()


# Глобальный debouncer для использования из разных мест
# (опционально, можно создавать отдельные инстансы)
_global_debouncer: Optional[DPIReloadDebouncer] = None


def get_global_debouncer(app: 'LupiDPIApp') -> DPIReloadDebouncer:
    """
    Возвращает глобальный debouncer (создает если не существует).

    Удобно для использования из разных частей UI где нет смысла
    создавать отдельные дебаунсеры.

    Args:
        app: Ссылка на главное приложение

    Returns:
        Глобальный экземпляр DPIReloadDebouncer
    """
    global _global_debouncer
    if _global_debouncer is None:
        _global_debouncer = DPIReloadDebouncer(app)
    return _global_debouncer


def schedule_dpi_reload(
    app: 'LupiDPIApp',
    reason: str,
    category_key: Optional[str] = None,
    delay_ms: int = 500
):
    """
    Удобная функция для планирования reload с debounce.

    Использует глобальный debouncer. Для независимого debounce
    используйте DPIReloadDebouncer напрямую.

    Args:
        app: Главное приложение
        reason: Причина перезагрузки
        category_key: Категория которая изменилась
        delay_ms: Задержка в миллисекундах (игнорируется после первого вызова)
    """
    debouncer = get_global_debouncer(app)
    debouncer.schedule_reload(reason, category_key)
