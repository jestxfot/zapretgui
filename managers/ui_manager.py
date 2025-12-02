# managers/ui_manager.py

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
        # ✅ Используем новый интерфейс NetworkPage
        if not hasattr(self.app, 'network_page'):
            log("network_page не найден, пропускаем обновление", "DEBUG")
            return
        
        # Определяем статус если не передан
        if is_enabled is None:
            if hasattr(self.app, 'hosts_ui_manager'):
                try:
                    is_enabled = self.app.hosts_ui_manager.check_hosts_entries_status()
                    log(f"Статус hosts записей: {is_enabled}", "DEBUG")
                except Exception as e:
                    log(f"Ошибка при проверке статуса hosts: {e}", "❌ ERROR")
                    is_enabled = False
            else:
                log("hosts_ui_manager не найден", "⚠ WARNING")
                is_enabled = False
        
        try:
            # ✅ Обновляем через метод страницы (новый дизайн)
            # is_blocked = НЕ is_enabled (если доступ включён, значит НЕ заблокирован)
            self.app.network_page.update_proxy_status(is_blocked=not is_enabled)
            log(f"Статус proxy обновлён: {'доступ включён' if is_enabled else 'доступ отключён'}", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при обновлении статуса proxy: {e}", "❌ ERROR")

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
            
            # Используем быструю проверку через реестр
            if service_running is None:
                from autostart.registry_check import is_autostart_enabled
                service_running = is_autostart_enabled()
                log(f"Быстрая проверка автозапуска через реестр: {service_running}", "DEBUG")

            # Обновляем страницу автозапуска
            if hasattr(self.app, 'autostart_page'):
                strategy_name = None
                if hasattr(self.app, 'current_strategy_label'):
                    strategy_name = self.app.current_strategy_label.text()
                self.app.autostart_page.update_status(service_running, strategy_name)

            # Обновляем кнопки запуска/остановки на страницах
            process_running = service_running
            if not service_running and hasattr(self.app, 'dpi_starter'):
                process_running = self.app.dpi_starter.check_process_running_wmi(silent=True)
            
            # Обновляем страницы
            if hasattr(self.app, 'home_page'):
                self.app.home_page.update_dpi_status(process_running)
            if hasattr(self.app, 'control_page'):
                self.app.control_page.update_status(process_running)
            
            log(f"✅ update_autostart_ui завершен: автозапуск={'включен' if service_running else 'выключен'}", "DEBUG")
                
        except Exception as e:
            log(f"❌ Ошибка в update_autostart_ui: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def update_ui_state(self, running: bool) -> None:
        """Обновляет состояние кнопок в зависимости от статуса запуска"""
        try:
            autostart_active = False
            if hasattr(self.app, 'service_manager'):
                autostart_active = self.app.service_manager.check_autostart_exists()
            
            # ✅ Обновляем новый интерфейс (страницы)
            self._update_pages_state(running, autostart_active)
            
        except Exception as e:
            log(f"Ошибка в update_ui_state: {e}", "❌ ERROR")
    
    def _update_pages_state(self, is_running: bool, autostart_active: bool) -> None:
        """Обновляет состояние страниц нового интерфейса"""
        try:
            # Получаем текущую стратегию
            strategy_name = None
            if hasattr(self.app, 'current_strategy_label'):
                strategy_name = self.app.current_strategy_label.text()
                if strategy_name == "Автостарт DPI отключен":
                    from config import get_last_strategy
                    strategy_name = get_last_strategy()
            
            # Обновляем главную страницу
            if hasattr(self.app, 'home_page'):
                self.app.home_page.update_dpi_status(is_running, strategy_name)
                
            # Обновляем страницу управления
            if hasattr(self.app, 'control_page'):
                self.app.control_page.update_status(is_running)
                if strategy_name:
                    self.app.control_page.update_strategy(strategy_name)
                    
            # Обновляем страницу стратегий
            if hasattr(self.app, 'strategies_page') and strategy_name:
                self.app.strategies_page.update_current_strategy(strategy_name)
                
            # Обновляем страницу автозапуска
            if hasattr(self.app, 'autostart_page'):
                self.app.autostart_page.update_status(autostart_active, strategy_name)
                
        except Exception as e:
            log(f"Ошибка в _update_pages_state: {e}", "DEBUG")

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
        """Обновляет отображение статуса процесса через страницы"""
        try:
            # Обновляем через страницы нового интерфейса
            if hasattr(self.app, 'home_page'):
                self.app.home_page.update_dpi_status(is_running)
            if hasattr(self.app, 'control_page'):
                self.app.control_page.update_status(is_running)
            if hasattr(self.app, 'autostart_page'):
                strategy_name = None
                if hasattr(self.app, 'current_strategy_label'):
                    strategy_name = self.app.current_strategy_label.text()
                self.app.autostart_page.update_status(autostart_active, strategy_name)
        except Exception as e:
            log(f"Ошибка в update_process_status_display: {e}", "❌ ERROR")

    def update_title_with_subscription_status(self, is_premium: bool, current_theme: str, 
                                             days_remaining: int, source: str = "api") -> None:
        """
        ✅ ОБНОВЛЕНО: Обновляет заголовок окна с информацией о подписке
        
        Args:
            is_premium: True если активна подписка
            current_theme: Текущая тема
            days_remaining: Дней до окончания (может быть None в offline)
            source: Источник данных ('api', 'offline', 'init')
        """
        try:
            from config import APP_VERSION
            
            base_title = f"Zapret2 v{APP_VERSION}"
            
            if is_premium:
                # ✅ ОБРАБОТКА ВСЕХ СЛУЧАЕВ
                if days_remaining is not None:
                    if days_remaining > 0:
                        if days_remaining <= 7:
                            # Скоро истекает - показываем количество дней
                            title = f"{base_title} - Premium ({days_remaining} дн.)"
                        else:
                            # Обычная премиум подписка
                            title = f"{base_title} - Premium"
                    elif days_remaining == 0:
                        # Истекает сегодня
                        title = f"{base_title} - Premium (истекает сегодня)"
                    else:
                        # Отрицательное значение (не должно быть в новой системе)
                        title = f"{base_title} - Premium (истёк)"
                else:
                    # None - offline режим или безлимитная подписка
                    if source == "offline":
                        title = f"{base_title} - Premium (offline)"
                    else:
                        title = f"{base_title} - Premium"
            else:
                title = base_title
            
            # Добавляем информацию о теме если она премиум
            if current_theme and "(Premium)" in current_theme:
                clean_theme = current_theme.replace(" (Premium)", "").replace(" (заблокировано)", "")
                title += f" | {clean_theme}"
            
            self.app.setWindowTitle(title)
            
            log(f"Заголовок обновлен: {title} (source: {source})", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при обновлении заголовка: {e}", "❌ ERROR")
            import traceback
            log(f"Traceback: {traceback.format_exc()}", "DEBUG")

    def update_subscription_button_text(self, is_premium: bool, days_remaining: int) -> None:
        """
        ✅ ОБНОВЛЕНО: Обновляет текст кнопки подписки
        
        Args:
            is_premium: True если активна подписка
            days_remaining: Дней до окончания (может быть None в offline)
        """
        try:
            if not hasattr(self.app, 'subscription_btn'):
                return
                
            if is_premium:
                # ✅ ОБРАБОТКА ВСЕХ СЛУЧАЕВ
                if days_remaining is not None:
                    if days_remaining > 0:
                        if days_remaining <= 7:
                            # Скоро истекает
                            self.app.subscription_btn.setText(f"Premium (осталось {days_remaining} дн.)")
                        else:
                            # Активная подписка
                            self.app.subscription_btn.setText("Premium активен")
                    elif days_remaining == 0:
                        # Истекает сегодня
                        self.app.subscription_btn.setText("Premium (истекает сегодня!)")
                    else:
                        # Отрицательное (не должно быть)
                        self.app.subscription_btn.setText("Premium истёк")
                else:
                    # None - offline или безлимит
                    self.app.subscription_btn.setText("Premium активен")
            else:
                self.app.subscription_btn.setText("Получить Premium")
            
            log(f"Текст кнопки подписки: {self.app.subscription_btn.text()}", "DEBUG")
                
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
