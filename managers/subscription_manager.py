from PyQt6.QtCore import QThread, QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from log import log


class SubscriptionManager:
    """Менеджер для работы с подписками и донатами"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.donate_checker = None
        
    def initialize_async(self):
        """Асинхронная инициализация и проверка подписки"""
        
        class SubscriptionInitWorker(QObject):
            finished = pyqtSignal(object, bool)  # donate_checker, success
            progress = pyqtSignal(str)
            
            def run(self):
                try:
                    self.progress.emit("Инициализация системы подписок...")
                    
                    # Создаем DonateChecker
                    from donater import DonateChecker
                    donate_checker = DonateChecker()
                    
                    self.progress.emit("Проверка статуса подписки...")
                    # Делаем первую проверку
                    donate_checker.check_subscription_status(use_cache=False)
                    
                    self.finished.emit(donate_checker, True)
                    
                except Exception as e:
                    log(f"Ошибка инициализации подписок: {e}", "❌ ERROR")
                    self.finished.emit(None, False)
        
        # Показываем что идет загрузка
        self.app.set_status("Инициализация подписок...")
        
        self._subscription_thread = QThread()
        self._subscription_worker = SubscriptionInitWorker()
        self._subscription_worker.moveToThread(self._subscription_thread)
        
        self._subscription_thread.started.connect(self._subscription_worker.run)
        self._subscription_worker.progress.connect(self.app.set_status)
        self._subscription_worker.finished.connect(self._on_subscription_ready)
        self._subscription_worker.finished.connect(self._subscription_thread.quit)
        self._subscription_worker.finished.connect(self._subscription_worker.deleteLater)
        self._subscription_thread.finished.connect(self._subscription_thread.deleteLater)
        
        self._subscription_thread.start()

    def _on_subscription_ready(self, donate_checker, success):
        """✅ ОБЪЕДИНЕННЫЙ обработчик готовности подписки"""
        if not success or not donate_checker:
            log("DonateChecker не инициализирован", "⚠ WARNING")
            # ✅ ИСПОЛЬЗУЕМ UI MANAGER
            if hasattr(self.app, 'ui_manager'):
                self.app.ui_manager.update_title_with_subscription_status(False, None, 0)
            self.app.set_status("Ошибка инициализации подписок")
            return

        # Сохраняем checker
        self.donate_checker = donate_checker
        self.app.donate_checker = donate_checker
        
        # ✅ ДОБАВЛЯЕМ ПРОВЕРКУ перед обновлением ссылки
        if hasattr(self.app, 'theme_manager'):
            self.app.theme_manager.donate_checker = donate_checker
            self.app.theme_manager.reapply_saved_theme_if_premium()
        else:
            log("theme_manager еще не готов, пропускаем обновление тем", "DEBUG")
            
        # Получаем информацию о подписке
        sub_info = donate_checker.get_full_subscription_info()
        
        # ✅ ИСПОЛЬЗУЕМ UI MANAGER для обновления UI
        current_theme = getattr(self.app.theme_manager, 'current_theme', None) if hasattr(self.app, 'theme_manager') else None
        
        if hasattr(self.app, 'ui_manager'):
            self.app.ui_manager.update_title_with_subscription_status(
                sub_info['is_premium'],
                current_theme,
                sub_info['days_remaining']
            )
            
            self.app.ui_manager.update_subscription_button_text(
                sub_info['is_premium'],
                sub_info['days_remaining']
            )

        # Обновляем темы через UI Manager
        if hasattr(self.app, 'theme_manager') and hasattr(self.app, 'ui_manager'):
            available_themes = self.app.theme_manager.get_available_themes()
            self.app.ui_manager.update_theme_combo(available_themes)
            
        self.app.set_status("Подписка инициализирована")
        log(f"Подписка готова: {'Premium' if sub_info['is_premium'] else 'Free'}", "INFO")

    def handle_subscription_status_change(self, was_premium, is_premium):
        """Обрабатывает изменение статуса подписки"""
        log(f"Статус подписки изменился: {was_premium} -> {is_premium}", "INFO")
        
        # ✅ ИСПОЛЬЗУЕМ UI MANAGER для обновления тем
        if hasattr(self.app, 'theme_manager') and hasattr(self.app, 'ui_manager'):
            available_themes = self.app.theme_manager.get_available_themes()
            current_selection = self.app.theme_combo.currentText()
            
            # Обновляем список тем через UI Manager
            self.app.ui_manager.update_theme_combo(available_themes)
            
            # Пытаемся восстановить выбор темы
            if current_selection in available_themes:
                self.app.theme_combo.setCurrentText(current_selection)
            else:
                # Ищем альтернативу
                self._find_alternative_theme(available_themes, current_selection)
        
        # Показываем уведомления
        self._show_subscription_notifications(was_premium, is_premium)
        
        # Обновляем UI элементы
        self._update_subscription_ui_elements()

    def _find_alternative_theme(self, available_themes, current_selection):
        """Находит альтернативную тему при изменении статуса подписки"""
        clean_theme_name = self.app.theme_manager.get_clean_theme_name(current_selection)
        
        # Ищем тему с таким же базовым именем
        theme_found = False
        for theme in available_themes:
            if self.app.theme_manager.get_clean_theme_name(theme) == clean_theme_name:
                self.app.theme_combo.setCurrentText(theme)
                theme_found = True
                break
        
        # Если не нашли похожую тему
        if not theme_found:
            for theme in available_themes:
                if "(заблокировано)" not in theme and "(Premium)" not in theme:
                    self.app.theme_combo.setCurrentText(theme)
                    self.app.theme_manager.apply_theme(theme)
                    log(f"Автоматически выбрана тема: {theme}", "INFO")
                    break

    def _show_subscription_notifications(self, was_premium, is_premium):
        """Показывает уведомления об изменении статуса подписки"""
        if is_premium and not was_premium:
            # Подписка активирована
            self.app.set_status("✅ Подписка активирована! Премиум темы доступны")
            
            if hasattr(self.app, 'tray_manager') and self.app.tray_manager:
                self.app.tray_manager.show_notification(
                    "Подписка активирована", 
                    "Премиум темы теперь доступны!"
                )
            
            QMessageBox.information(
                self.app,
                "Подписка активирована",
                "Ваша Premium подписка успешно активирована!\n\n"
                "Теперь вам доступны:\n"
                "• Эксклюзивные темы оформления\n"
                "• Приоритетная поддержка\n"
                "• Ранний доступ к новым функциям\n\n"
                "Спасибо за поддержку проекта!"
            )
            
        elif not is_premium and was_premium:
            # Подписка истекла
            self.app.set_status("❌ Подписка истекла. Премиум темы недоступны")
            
            if hasattr(self.app, 'tray_manager') and self.app.tray_manager:
                self.app.tray_manager.show_notification(
                    "Подписка истекла", 
                    "Премиум темы больше недоступны"
                )
            
            self._show_subscription_expired_dialog()

    def _show_subscription_expired_dialog(self):
        """Показывает диалог истечения подписки"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Подписка истекла")
        msg.setText("Ваша Premium подписка истекла")
        msg.setInformativeText(
            "Премиум функции больше недоступны.\n\n"
            "Чтобы продолжить использовать эксклюзивные темы "
            "и другие преимущества, пожалуйста, продлите подписку."
        )
        
        msg.addButton("Продлить подписку", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Позже", QMessageBox.ButtonRole.RejectRole)
        
        if msg.exec() == 0:  # Кнопка "Продлить подписку"
            self.app.show_subscription_dialog()

    def _update_subscription_ui_elements(self):
        """Обновляет UI элементы, зависящие от подписки"""
        try:
            # ✅ ИСПОЛЬЗУЕМ UI MANAGER
            if hasattr(self.app, 'ui_manager'):
                self.app.ui_manager.update_proxy_button_state()
            
            if hasattr(self.app, 'button_grid'):
                self.app.button_grid.update()
            
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
        except Exception as e:
            log(f"Ошибка при обновлении UI после изменения подписки: {e}", "❌ ERROR")

    def update_subscription_ui(self):
        """Обновляет UI после проверки подписки"""
        try:
            # Проверяем наличие theme_manager
            if not hasattr(self.app, 'theme_manager'):
                log("theme_manager еще не инициализирован, пропускаем обновление", "DEBUG")
                return
            
            if not self.donate_checker:
                return
                
            is_premium, status_msg, days_remaining = self.donate_checker.check_subscription_status()
            
            # ✅ Эту проверку можно упростить, так как мы уже знаем что theme_manager существует
            current_theme = self.app.theme_manager.current_theme  # Убрали избыточную проверку
            
            # ✅ ИСПОЛЬЗУЕМ UI MANAGER
            if hasattr(self.app, 'ui_manager'):
                self.app.ui_manager.update_title_with_subscription_status(is_premium, current_theme, days_remaining)
                
                # Обновляем темы через UI Manager
                if hasattr(self.app, 'theme_manager'):
                    available_themes = self.app.theme_manager.get_available_themes()
                    current_selection = self.app.theme_combo.currentText()
                    
                    self.app.ui_manager.update_theme_combo(available_themes)
                    
                    if current_selection in available_themes:
                        self.app.theme_combo.setCurrentText(current_selection)
            
            self.app.set_status("Проверка подписки завершена")
            log(f"Статус подписки обновлен: {'Premium' if is_premium else 'Free'}", "INFO")
            
        except Exception as e:
            log(f"Ошибка при обновлении UI подписки: {e}", "❌ ERROR")
            self.app.set_status("Ошибка проверки подписки")