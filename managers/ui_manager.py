from PyQt6.QtWidgets import QApplication
from pathlib import Path
from log import log
import qtawesome as qta
from PyQt6.QtCore import QSize
import time

class UIManager:
    """Менеджер для управления UI компонентами и их логикой"""
    
    def __init__(self, app_instance):
        self.app = app_instance

    def update_theme_combo(self, available_themes: list) -> None:
        """Обновляет список доступных тем в комбо-боксе с учетом подписки"""
        # Если theme_handler доступен, используем его
        if hasattr(self.app, 'theme_handler') and self.app.theme_handler is not None:
            self.app.theme_handler.update_available_themes()
            return
        
        # Fallback - прямое обновление комбо-бокса
        if not hasattr(self.app, 'theme_combo'):
            return
            
        current_theme = self.app.theme_combo.currentText()
        
        # Временно отключаем сигналы чтобы избежать лишних срабатываний
        self.app.theme_combo.blockSignals(True)
        
        # Очищаем и заполняем заново
        self.app.theme_combo.clear()
        self.app.theme_combo.addItems(available_themes)
        
        # Применяем стили для заблокированных элементов
        self._apply_theme_combo_styles()
        
        # Восстанавливаем выбор, если тема доступна
        clean_current = current_theme
        if hasattr(self.app, 'theme_manager'):
            clean_current = self.app.theme_manager.get_clean_theme_name(current_theme)
        
        for theme in available_themes:
            clean_theme = theme
            if hasattr(self.app, 'theme_manager'):
                clean_theme = self.app.theme_manager.get_clean_theme_name(theme)
            if clean_theme == clean_current:
                self.app.theme_combo.setCurrentText(theme)
                break
        else:
            # Если текущая тема недоступна, выбираем первую доступную
            if available_themes:
                # Ищем первую незаблокированную тему
                for theme in available_themes:
                    if "(заблокировано)" not in theme and "(Premium)" not in theme:
                        self.app.theme_combo.setCurrentText(theme)
                        break
                else:
                    # Если все темы заблокированы (не должно происходить), выбираем первую
                    self.app.theme_combo.setCurrentText(available_themes[0])
        
        # Включаем сигналы обратно
        self.app.theme_combo.blockSignals(False)
        
        # Если произошло изменение темы, сигнализируем об этом
        new_theme = self.app.theme_combo.currentText()
        if new_theme != current_theme:
            self.app.theme_changed.emit(new_theme)

    def update_proxy_button_state(self, is_enabled: bool = None) -> None:
        """Обновляет состояние кнопки proxy на основе статуса hosts"""
        if not hasattr(self.app, 'proxy_button'):
            log("proxy_button не найден, пропускаем обновление", "DEBUG")
            return
        
        # ✅ УПРОЩЕННАЯ ЛОГИКА: Используем hosts_ui_manager
        if is_enabled is None:
            if hasattr(self.app, 'hosts_ui_manager'):
                try:
                    # ✅ ВЫЗЫВАЕМ ПРАВИЛЬНЫЙ МЕТОД
                    is_enabled = self.app.hosts_ui_manager.check_hosts_entries_status()
                    log(f"Статус hosts записей: {is_enabled}", "DEBUG")
                except Exception as e:
                    log(f"Ошибка при проверке статуса hosts: {e}", "❌ ERROR")
                    is_enabled = False
            else:
                log("hosts_ui_manager не найден", "⚠ WARNING")
                is_enabled = False
            
        config = self.get_proxy_button_config()
        
        try:
            if is_enabled:
                # Кнопка показывает "отключить"
                state = config['enabled_state']
            else:
                # Кнопка показывает "включить"
                state = config['disabled_state']
            
            # Обновляем текст, иконку и стиль
            self.app.proxy_button.setText(f" {state['short_text']}")
            self.app.proxy_button.setIcon(qta.icon(state['icon'], color='white'))
            self.app.proxy_button.setIconSize(QSize(16, 16))
            self.app.proxy_button.setToolTip(state['tooltip'])
            
            from ui.theme import BUTTON_STYLE
            self.app.proxy_button.setStyleSheet(BUTTON_STYLE.format(state['color']))
            
            log(f"Кнопка proxy обновлена: {'включено' if is_enabled else 'выключено'}", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при обновлении кнопки proxy: {e}", "❌ ERROR")

    def force_enable_combos(self) -> bool:
        """Принудительно включает комбо-боксы тем"""
        try:
            if hasattr(self.app, 'theme_combo'):
                from ui.theme import COMMON_STYLE
                # Полное восстановление состояния комбо-бокса тем
                self.app.theme_combo.setEnabled(True)
                self.app.theme_combo.show()
                self.app.theme_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center;")

            # Принудительное обновление UI
            QApplication.processEvents()
            
            # Возвращаем True если комбо-бокс существует и активен
            return hasattr(self.app, 'theme_combo') and self.app.theme_combo.isEnabled()
        except Exception as e:
            log(f"Ошибка при активации комбо-бокса тем: {str(e)}")
            return False

    def update_autostart_ui(self, service_running: bool) -> None:
        """Обновляет интерфейс при включении/выключении автозапуска"""
        try:
            log(f"🔴 update_autostart_ui начат: service_running={service_running}", "DEBUG")
            
            # ✅ Используем быструю проверку через реестр
            if service_running is None:
                from autostart.registry_check import is_autostart_enabled
                service_running = is_autostart_enabled()
                log(f"Быстрая проверка автозапуска через реестр: {service_running}", "DEBUG")

            # Убеждаемся, что оба стека всегда находятся в правильных позициях
            # и имеют правильные размеры
            
            # Сначала удаляем виджеты из сетки (если они там есть)
            if hasattr(self.app, 'button_grid') and hasattr(self.app, 'start_stop_stack') and hasattr(self.app, 'autostart_stack'):
                self.app.button_grid.removeWidget(self.app.start_stop_stack)
                self.app.button_grid.removeWidget(self.app.autostart_stack)
                
                # Добавляем обратно в правильные позиции - ВСЕГДА по одной колонке на каждый
                self.app.button_grid.addWidget(self.app.start_stop_stack, 0, 0, 1, 1)  # строка 0, колонка 0, 1 строка, 1 колонка
                self.app.button_grid.addWidget(self.app.autostart_stack, 0, 1, 1, 1)   # строка 0, колонка 1, 1 строка, 1 колонка
                
                # Убеждаемся, что оба стека видимы
                self.app.start_stop_stack.setVisible(True)
                self.app.autostart_stack.setVisible(True)
                
                if service_running:
                    # ✅ АВТОЗАПУСК АКТИВЕН
                    # Показываем кнопку отключения автозапуска
                    if hasattr(self.app, 'autostart_disable_btn'):
                        self.app.autostart_stack.setCurrentWidget(self.app.autostart_disable_btn)
                    
                    # В левой колонке показываем кнопку остановки
                    # (так как при автозапуске процесс обычно запущен)
                    if hasattr(self.app, 'stop_btn'):
                        self.app.start_stop_stack.setCurrentWidget(self.app.stop_btn)
                    
                else:
                    # ✅ АВТОЗАПУСК ВЫКЛЮЧЕН
                    # Показываем кнопку включения автозапуска
                    if hasattr(self.app, 'autostart_enable_btn'):
                        self.app.autostart_stack.setCurrentWidget(self.app.autostart_enable_btn)
                    
                    # Обновляем состояние кнопок запуска/остановки
                    process_running = self.app.dpi_starter.check_process_running_wmi(silent=True) if hasattr(self.app, 'dpi_starter') else False
                    if process_running and hasattr(self.app, 'stop_btn'):
                        self.app.start_stop_stack.setCurrentWidget(self.app.stop_btn)
                    elif hasattr(self.app, 'start_btn'):
                        self.app.start_stop_stack.setCurrentWidget(self.app.start_btn)
                
                # Принудительное обновление layout
                self.app.button_grid.update()
                QApplication.processEvents()
            else:
                log("Не все виджеты кнопок найдены для обновления autostart UI", "⚠ WARNING")
                
        except Exception as e:
            log(f"❌ Ошибка в update_autostart_ui: {e}", "ERROR")

    def update_ui_state(self, running: bool) -> None:
        """Обновляет состояние кнопок в зависимости от статуса запуска"""
        try:
            autostart_active = False
            if hasattr(self.app, 'service_manager'):
                autostart_active = self.app.service_manager.check_autostart_exists()
            
            # Если автозапуск НЕ активен, управляем кнопками запуска/остановки
            if not autostart_active:
                if running:
                    # Показываем кнопку остановки
                    if hasattr(self.app, 'start_stop_stack') and hasattr(self.app, 'stop_btn'):
                        self.app.start_stop_stack.setCurrentWidget(self.app.stop_btn)
                else:
                    # Показываем кнопку запуска
                    if hasattr(self.app, 'start_stop_stack') and hasattr(self.app, 'start_btn'):
                        self.app.start_stop_stack.setCurrentWidget(self.app.start_btn)
        except Exception as e:
            log(f"Ошибка в update_ui_state: {e}", "❌ ERROR")

    def update_button_visibility(self, is_running: bool, autostart_active: bool) -> None:
        """Обновляет видимость кнопок запуска/остановки"""
        try:
            if not hasattr(self.app, 'start_btn') or not hasattr(self.app, 'stop_btn'):
                return
                
            if is_running or autostart_active:
                self.app.start_btn.setVisible(False)
                self.app.stop_btn.setVisible(True)
            else:
                self.app.start_btn.setVisible(True)
                self.app.stop_btn.setVisible(False)
        except Exception as e:
            log(f"Ошибка в update_button_visibility: {e}", "❌ ERROR")

    def update_process_status_display(self, is_running: bool, autostart_active: bool) -> None:
        """Обновляет отображение статуса процесса"""
        try:
            if not hasattr(self.app, 'process_status_value'):
                return
                
            if autostart_active:
                self.app.process_status_value.setText("АВТОЗАПУСК АКТИВЕН")
                self.app.process_status_value.setStyleSheet("color: purple; font-weight: bold;")
            else:
                if is_running:
                    self.app.process_status_value.setText("ВКЛЮЧЕН")
                    self.app.process_status_value.setStyleSheet("color: green; font-weight: bold;")
                else:
                    self.app.process_status_value.setText("ВЫКЛЮЧЕН")
                    self.app.process_status_value.setStyleSheet("color: red; font-weight: bold;")
        except Exception as e:
            log(f"Ошибка в update_process_status_display: {e}", "❌ ERROR")

    def update_title_with_subscription_status(self, is_premium: bool, current_theme: str, days_remaining: int) -> None:
        """Обновляет заголовок окна с информацией о подписке"""
        try:
            from config import APP_VERSION
            
            base_title = f"Zapret v{APP_VERSION}"
            
            if is_premium:
                if days_remaining > 0:
                    if days_remaining <= 7:
                        # Скоро истекает - показываем количество дней
                        title = f"{base_title} - Premium ({days_remaining} дн.)"
                    else:
                        # Обычная премиум подписка
                        title = f"{base_title} - Premium"
                else:
                    # Истекшая подписка
                    title = f"{base_title} - Premium (истекла)"
            else:
                title = base_title
            
            # Добавляем информацию о теме если она премиум
            if current_theme and "(Premium)" in current_theme:
                clean_theme = current_theme.replace(" (Premium)", "").replace(" (заблокировано)", "")
                title += f" | {clean_theme}"
            
            self.app.setWindowTitle(title)
            
        except Exception as e:
            log(f"Ошибка при обновлении заголовка: {e}", "❌ ERROR")

    def update_subscription_button_text(self, is_premium: bool, days_remaining: int) -> None:
        """Обновляет текст кнопки подписки"""
        try:
            if not hasattr(self.app, 'subscription_btn'):
                return
                
            if is_premium:
                if days_remaining > 0:
                    if days_remaining <= 7:
                        # Скоро истекает
                        self.app.subscription_btn.setText(f"Premium (осталось {days_remaining} дн.)")
                    else:
                        # Активная подписка
                        self.app.subscription_btn.setText("Premium активен")
                else:
                    # Истекшая подписка
                    self.app.subscription_btn.setText("Premium истек")
            else:
                self.app.subscription_btn.setText("Получить Premium")
                
        except Exception as e:
            log(f"Ошибка при обновлении кнопки подписки: {e}", "❌ ERROR")

    def update_strategies_list(self, force_update: bool = False) -> None:
        """Обновляет список доступных стратегий"""
        log("🔵 update_strategies_list начат", "DEBUG")
        
        try:
            if not hasattr(self.app, 'strategy_manager'):
                log("Strategy manager не инициализирован", "❌ ERROR")
                return
                
            # Получаем список стратегий
            log("🔵 Получаем список стратегий из manager", "DEBUG")
            strategies = self.app.strategy_manager.get_strategies_list(force_update=force_update)
            log(f"🔵 Получено стратегий: {len(strategies) if strategies else 0}", "DEBUG")
            
            # Сохраняем текущий выбор
            current_strategy = None
            if hasattr(self.app, 'current_strategy_name') and self.app.current_strategy_name:
                current_strategy = self.app.current_strategy_name
            elif hasattr(self.app, 'current_strategy_label'):
                current_strategy = self.app.current_strategy_label.text()
                if current_strategy == "Автостарт DPI отключен":
                    from config import get_last_strategy
                    current_strategy = get_last_strategy()
            
            # Обновляем текущую метку, если стратегия выбрана
            if current_strategy and current_strategy != "Автостарт DPI отключен" and hasattr(self.app, 'current_strategy_label'):
                self.app.current_strategy_label.setText(current_strategy)
            
            log(f"Загружено {len(strategies)} стратегий", level="INFO")
            
        except Exception as e:
            error_msg = f"Ошибка при обновлении списка стратегий: {str(e)}"
            log(error_msg, level="❌ ERROR")
            if hasattr(self.app, 'set_status'):
                self.app.set_status(error_msg)
        finally:
            log("🔵 update_strategies_list завершен", "DEBUG")

    def _apply_theme_combo_styles(self) -> None:
        """Применяет стили к комбо-боксу тем для выделения заблокированных элементов"""
        # Проверяем, что theme_handler инициализирован
        if hasattr(self.app, 'theme_handler') and self.app.theme_handler is not None:
            self.app.theme_handler.update_theme_combo_styles()
        else:
            # Fallback для случаев когда theme_handler еще не инициализирован
            log("theme_handler не инициализирован, используем fallback стили", "DEBUG")
            try:
                from ui.theme import COMMON_STYLE
                style = f"""
                QComboBox {{
                    {COMMON_STYLE}
                    text-align: center;
                    font-size: 10pt;
                    padding: 5px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }}
                """
                if hasattr(self.app, 'theme_combo'):
                    self.app.theme_combo.setStyleSheet(style)
            except Exception as e:
                log(f"Ошибка применения fallback стилей: {e}", "❌ ERROR")

    def get_proxy_button_config(self) -> dict:
        """
        Возвращает конфигурацию для различных состояний кнопки proxy.
        
        Returns:
            dict: Конфигурация состояний кнопки
        """
        return {
            'enabled_state': {
                'full_text': 'Отключить доступ к ChatGPT, Spotify, Twitch',
                'short_text': 'Отключить разблокировку',
                'color': "255, 93, 174",
                'icon': 'fa5s.lock',
                'tooltip': 'Нажмите чтобы отключить разблокировку сервисов через hosts-файл'
            },
            'disabled_state': {
                'full_text': 'Разблокировать ChatGPT, Spotify, Twitch и др.',
                'short_text': 'Разблокировать сервисы',
                'color': "218, 165, 32",
                'icon': 'fa5s.unlock',
                'tooltip': 'Нажмите чтобы разблокировать популярные сервисы через hosts-файл'
            }
        }