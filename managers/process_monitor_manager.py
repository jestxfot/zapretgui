from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor
from log import log


class ProcessMonitorManager(QObject):
    """Менеджер для мониторинга процессов DPI"""
    
    # ● Огонёк-индикатор (Unicode filled circle)
    INDICATOR_CHAR = '●'
    
    # Цвет текста (статичный тёмно-зелёный)
    TEXT_COLOR = "#00AA00"
    # Цвет огонька (всегда яркий)
    INDICATOR_COLOR = "#00FF00"
    
    # Фазы пульсации: (blur_radius, alpha 0-255) для QGraphicsDropShadowEffect
    # Тень плавно увеличивается и уменьшается (эффект "дыхания")
    RADAR_PHASES = [
        (8, 80),     # Минимум
        (12, 100),   # Нарастает
        (16, 130),   
        (20, 160),   
        (24, 190),   
        (28, 220),   
        (32, 255),   # Максимум
        (28, 220),   # Спадает
        (24, 190),   
        (20, 160),   
        (16, 130),   
        (12, 100),   
        (8, 80),     # Минимум
    ]
    
    # Фазы для проверки: (blur_radius, alpha 0-255) синяя тень
    CHECK_PHASES = [
        (5, 80),
        (10, 150),
        (15, 200),
        (20, 255),
        (15, 200),
        (10, 150),
        (5, 80),
    ]
    
    # Цвета
    CHECK_TEXT_COLOR = "#1976D2"
    CHECK_INDICATOR_COLOR = "#2196F3"
    
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.process_monitor = None
        
        # Для анимации проверки
        self._check_index = 0
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._animate_check)
        self._is_checking = False
        
        # Для анимации индикатора ВКЛЮЧЕН (пульсация маяка)
        self._pulse_index = 0
        self._indicator_timer = QTimer()
        self._indicator_timer.timeout.connect(self._animate_indicator)
        self._is_running = False

    def initialize_process_monitor(self):
        """Инициализирует поток мониторинга процесса"""
        if hasattr(self.app, 'process_monitor') and self.app.process_monitor is not None:
            self.app.process_monitor.stop()
        
        from config.process_monitor import ProcessMonitorThread
        
        self.process_monitor = ProcessMonitorThread(self.app.dpi_starter)
        self.app.process_monitor = self.process_monitor  # Сохраняем ссылку в app
        
        # Подключаем все сигналы
        self.process_monitor.processStatusChanged.connect(self.on_process_status_changed)
        self.process_monitor.checkingStarted.connect(self._on_checking_started)
        self.process_monitor.checkingFinished.connect(self._on_checking_finished)
        self.process_monitor.start()
        
        log("Process Monitor инициализирован", "INFO")
    
    def _on_checking_started(self):
        """Вызывается когда начинается проверка процесса"""
        self._is_checking = True
        self._check_index = 0
        self._indicator_timer.stop()  # Останавливаем пульсацию
        self._check_timer.start(200)  # Точки мигают каждые 200мс
        self._update_checking_display()
    
    def _on_checking_finished(self):
        """Вызывается когда проверка завершена"""
        self._is_checking = False
        self._check_timer.stop()
        
        # ✅ Обновляем статус после завершения проверки
        self._restore_status_display()
    
    def _animate_check(self):
        """Анимация пульсации для проверки"""
        if self._is_checking:
            self._check_index = (self._check_index + 1) % len(self.CHECK_PHASES)
            self._update_checking_display()
    
    def _animate_indicator(self):
        """Анимация радара для ВКЛЮЧЕН - волна расширяется наружу"""
        if self._is_running and not self._is_checking:
            self._pulse_index = (self._pulse_index + 1) % len(self.RADAR_PHASES)
            self._update_running_display()
    
    def _update_checking_display(self):
        """Обновляет отображение статуса проверки - пульсирующая синяя тень"""
        if not hasattr(self.app, 'process_status_value'):
            return
        
        try:
            blur_radius, alpha = self.CHECK_PHASES[self._check_index]
            
            # Применяем QGraphicsDropShadowEffect для синей тени
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(blur_radius)
            shadow_effect.setColor(QColor(33, 150, 243, alpha))  # Синяя тень
            shadow_effect.setOffset(0, 0)
            self.app.process_status_value.setGraphicsEffect(shadow_effect)
            
            # HTML: огонёк + текст
            html = (
                f'<span style="color: {self.CHECK_INDICATOR_COLOR};">{self.INDICATOR_CHAR}</span>'
                f'<span style="color: {self.CHECK_TEXT_COLOR};"> проверка</span>'
            )
            self.app.process_status_value.setText(html)
            self.app.process_status_value.setStyleSheet("font-weight: bold; font-size: 10pt;")
        except Exception as e:
            log(f"Ошибка _update_checking_display: {e}", "DEBUG")
    
    def _update_running_display(self):
        """Обновляет отображение ВКЛЮЧЕН - пульсирующая тень под индикатором"""
        if not hasattr(self.app, 'process_status_value'):
            return
        
        try:
            blur_radius, alpha = self.RADAR_PHASES[self._pulse_index]
            
            # Применяем QGraphicsDropShadowEffect для настоящей тени
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(blur_radius)
            shadow_effect.setColor(QColor(0, 255, 0, alpha))  # Зелёная тень
            shadow_effect.setOffset(0, 0)  # Тень по центру (свечение)
            self.app.process_status_value.setGraphicsEffect(shadow_effect)
            
            # HTML: яркий огонёк + текст
            html = (
                f'<span style="color: {self.INDICATOR_COLOR};">{self.INDICATOR_CHAR}</span>'
                f'<span style="color: {self.TEXT_COLOR};"> ВКЛЮЧЕН</span>'
            )
            self.app.process_status_value.setText(html)
            self.app.process_status_value.setStyleSheet("font-weight: bold; font-size: 10pt;")
        except Exception as e:
            log(f"Ошибка _update_running_display: {e}", "DEBUG")
    
    def _restore_status_display(self):
        """Восстанавливает отображение статуса после проверки"""
        try:
            # Получаем текущее состояние
            is_running = getattr(self.app, '_prev_running', False)
            self._is_running = is_running
            
            from autostart.registry_check import is_autostart_enabled
            autostart_active = is_autostart_enabled() if hasattr(self.app, 'service_manager') else False
            
            if autostart_active:
                # Автозапуск - статичный фиолетовый с фиолетовой тенью
                self._indicator_timer.stop()
                if hasattr(self.app, 'process_status_value'):
                    # Статичная фиолетовая тень
                    shadow_effect = QGraphicsDropShadowEffect()
                    shadow_effect.setBlurRadius(15)
                    shadow_effect.setColor(QColor(156, 39, 176, 150))  # Фиолетовая
                    shadow_effect.setOffset(0, 0)
                    self.app.process_status_value.setGraphicsEffect(shadow_effect)
                    
                    html = (
                        f'<span style="color: #9C27B0;">{self.INDICATOR_CHAR}</span>'
                        f'<span style="color: #7B1FA2;"> АВТОЗАПУСК</span>'
                    )
                    self.app.process_status_value.setText(html)
                    self.app.process_status_value.setStyleSheet("font-weight: bold; font-size: 10pt;")
            elif is_running:
                # ВКЛЮЧЕН - запускаем пульсацию маяка
                self._pulse_index = 0
                self._update_running_display()
                self._indicator_timer.start(80)  # Плавная пульсация каждые 80мс
            else:
                # ВЫКЛЮЧЕН - статичный красный, убираем тень
                self._indicator_timer.stop()
                if hasattr(self.app, 'process_status_value'):
                    # Убираем эффект тени
                    self.app.process_status_value.setGraphicsEffect(None)
                    
                    html = (
                        f'<span style="color: #FF4444;">{self.INDICATOR_CHAR}</span>'
                        f'<span style="color: #CC3333;"> ВЫКЛЮЧЕН</span>'
                    )
                    self.app.process_status_value.setText(html)
                    self.app.process_status_value.setStyleSheet("font-weight: bold; font-size: 10pt;")
                    
        except Exception as e:
            log(f"Ошибка восстановления статуса: {e}", "DEBUG")

    def on_process_status_changed(self, is_running):
        """Обрабатывает сигнал изменения статуса процесса"""
        try:
            # Проверяем, изменилось ли состояние автозапуска
            from autostart.registry_check import is_autostart_enabled
            autostart_active = is_autostart_enabled() if hasattr(self.app, 'service_manager') else False
            
            # Сохраняем текущее состояние для сравнения в будущем
            if not hasattr(self.app, '_prev_autostart'):
                self.app._prev_autostart = False
            if not hasattr(self.app, '_prev_running'):
                self.app._prev_running = False
                
            self.app._prev_autostart = autostart_active
            self.app._prev_running = is_running
            self._is_running = is_running
            
            # Обновляем кнопки через UI Manager
            if hasattr(self.app, 'ui_manager'):
                self.app.ui_manager.update_button_visibility(is_running, autostart_active)
            
            # ✅ Используем нашу анимированную версию отображения статуса
            self._restore_status_display()
            
        except Exception as e:
            log(f"Ошибка в on_process_status_changed: {e}", level="❌ ERROR")

    def stop_monitoring(self):
        """Останавливает мониторинг процесса"""
        # Останавливаем все таймеры анимации
        self._check_timer.stop()
        self._indicator_timer.stop()
        
        if self.process_monitor:
            self.process_monitor.stop()
            log("Process Monitor остановлен", "INFO")