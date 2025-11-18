"""
Диалог показа статуса серверов обновлений и последних версий
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QTableWidgetItem,
                            QGroupBox, QProgressBar, QTabWidget, QWidget,
                            QHeaderView, QFrame, QTextEdit, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QIcon
import os
from datetime import datetime
from typing import Dict, Any, Optional
import time

from config import APP_VERSION, CHANNEL, ICON_PATH, ICON_TEST_PATH, get_auto_update_enabled, set_auto_update_enabled
from log import log


class ServerCheckWorker(QThread):
    """Воркер для проверки статуса серверов"""
    
    server_checked = pyqtSignal(str, dict)  # server_name, status
    all_complete = pyqtSignal()
    
    def __init__(self):
        super().__init__()
    
    def run(self):
        """Проверяет все сервера из пула"""
        from updater.github_release import check_rate_limit
        from updater.server_pool import get_server_pool
        import requests
        import time as _time

        pool = get_server_pool()
        
        # ─────────────────────────────────────────────
        # 1. Проверяем все VPS сервера из пула
        # ─────────────────────────────────────────────
        for server in pool.servers:
            server_id = server['id']
            server_name = f"{server['name']}"
            
            # Получаем статистику сервера
            stats = pool.stats.get(server_id, {})
            blocked_until = stats.get('blocked_until')
            current_time = _time.time()
            
            # Проверяем блокировку
            if blocked_until and current_time < blocked_until:
                from datetime import datetime
                until_dt = datetime.fromtimestamp(blocked_until)
                
                status = {
                    'status': 'blocked',
                    'response_time': 0,
                    'url': f"https://{server['host']}:{server['https_port']}",
                    'error': f"Заблокирован до {until_dt.strftime('%H:%M:%S')}",
                    'is_current': server_id == pool.selected_server['id'],
                    'server_id': server_id
                }
                
                self.server_checked.emit(server_name, status)
                _time.sleep(0.1)
                continue
            
            # Проверяем HTTPS
            log(f"Проверка {server_name}...", "🌐 STATUS")
            
            start_time = _time.time()
            try:
                https_url = f"https://{server['host']}:{server['https_port']}/api/all_versions.json"
                
                from updater.server_config import should_verify_ssl
                verify_ssl = should_verify_ssl()
                
                if not verify_ssl:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                response = requests.get(
                    https_url,
                    timeout=10,
                    verify=verify_ssl,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "Zapret-Updater/3.1"
                    }
                )
                
                response_time = _time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    stable_version = data.get('stable', {}).get('version', 'н/д')
                    test_version = data.get('test', {}).get('version', 'н/д')
                    
                    ssl_status = "🔒 SSL" if verify_ssl else "🔓"
                    
                    status = {
                        'status': 'online',
                        'response_time': response_time,
                        'url': f"{server['host']}:{server['https_port']} {ssl_status}",
                        'stable_version': stable_version,
                        'test_version': test_version,
                        'error': '',
                        'is_current': server_id == pool.selected_server['id'],
                        'priority': server['priority'],
                        'weight': server['weight'],
                        'server_id': server_id
                    }
                    
                    # Записываем успех
                    pool.record_success(server_id, response_time)
                    
                    log(f"✅ {server_name} онлайн ({response_time*1000:.0f}мс)", "🌐 STATUS")
                else:
                    status = {
                        'status': 'error',
                        'response_time': response_time,
                        'url': f"{server['host']}:{server['https_port']}",
                        'error': f'HTTP {response.status_code}',
                        'is_current': server_id == pool.selected_server['id'],
                        'server_id': server_id
                    }
                    
                    pool.record_failure(server_id, f"HTTP {response.status_code}")
                    
            except Exception as e:
                error_msg = str(e)[:40]
                
                status = {
                    'status': 'error',
                    'response_time': _time.time() - start_time if start_time else 0,
                    'url': f"{server['host']}:{server['https_port']}",
                    'error': error_msg,
                    'is_current': server_id == pool.selected_server['id'],
                    'server_id': server_id
                }
                
                pool.record_failure(server_id, error_msg)
                log(f"❌ {server_name}: {error_msg}", "🌐 STATUS")
            
            self.server_checked.emit(server_name, status)
            _time.sleep(0.2)
        
        # ─────────────────────────────────────────────
        # 2. Проверяем GitHub API
        # ─────────────────────────────────────────────
        log("Проверка GitHub API...", "🌐 STATUS")
        
        try:
            rate_info = check_rate_limit()
            github_status = {
                'status': 'online',
                'response_time': 0.5,
                'rate_limit': rate_info['remaining'],
                'rate_limit_max': rate_info['limit'],
                'reset_time': rate_info.get('reset_dt', None),
                'error': ''
            }
            log(f"✅ GitHub API онлайн: {rate_info['remaining']}/{rate_info['limit']}", "🌐 STATUS")
        except Exception as e:
            github_status = {
                'status': 'error',
                'error': str(e)[:50],
                'response_time': 0
            }
            log(f"❌ GitHub API ошибка: {e}", "🌐 STATUS")
        
        self.server_checked.emit('GitHub API', github_status)
        
        self.all_complete.emit()


class VersionCheckWorker(QThread):
    """Воркер для получения информации о версиях"""
    
    version_found = pyqtSignal(str, dict)  # channel, version_info
    complete = pyqtSignal()
    
    def run(self):
        """Получает информацию о последних версиях"""
        from updater.release_manager import get_latest_release
        
        channels = ['stable', 'dev']
        
        for channel in channels:
            log(f"Получение версии для канала {channel}...", "📦 VERSION")
            
            try:
                # ✅ ИСПОЛЬЗУЕМ КЭШ при проверке в диалоге
                release = get_latest_release(channel, use_cache=True)
                if release:
                    log(f"✅ {channel}: найдена версия {release['version']} (источник: {release.get('source', 'н/д')})", "📦 VERSION")
                    self.version_found.emit(channel, release)
                else:
                    log(f"❌ {channel}: не удалось получить версию", "📦 VERSION")
                    self.version_found.emit(channel, {'error': 'Не удалось получить версию'})
            except Exception as e:
                log(f"❌ {channel}: ошибка {e}", "📦 VERSION")
                self.version_found.emit(channel, {'error': str(e)})
            
            time.sleep(0.2)
        
        self.complete.emit()


class ServerStatusDialog(QDialog):
    """Диалог статуса серверов и версий"""
    
    update_requested = pyqtSignal()  # Сигнал для запуска обновления
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("📊 Статус серверов обновлений")
        self.setMinimumSize(700, 550)
        
        # Устанавливаем иконку
        icon_path = ICON_TEST_PATH if CHANNEL == "test" else ICON_PATH
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.server_worker = None
        self.version_worker = None
        
        self.init_ui()
        
        # Автоматически начинаем проверку
        QTimer.singleShot(100, self.start_checks)
    
    def init_ui(self):
        """Создаёт интерфейс"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Заголовок
        title = QLabel("🌐 Мониторинг серверов обновлений Zapret")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Информация о текущей версии
        current_info = QLabel(f"Ваша версия: {APP_VERSION} (канал: {CHANNEL})")
        current_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_info.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addWidget(current_info)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("QFrame { color: #ddd; }")
        layout.addWidget(line)
        
        # Табы
        self.tabs = QTabWidget()
        
        # Вкладка серверов
        self.servers_tab = QWidget()
        self._create_servers_tab()
        self.tabs.addTab(self.servers_tab, "🖥️ Сервера")
        
        # Вкладка версий
        self.versions_tab = QWidget()
        self._create_versions_tab()
        self.tabs.addTab(self.versions_tab, "📦 Версии")
        
        # Вкладка статистики
        self.stats_tab = QWidget()
        self._create_stats_tab()
        self.tabs.addTab(self.stats_tab, "📊 Статистика")
        
        layout.addWidget(self.tabs)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #f0f0f0;
            }
            QProgressBar::chunk {
                background: #3daee9;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Статус
        self.status_label = QLabel("Готов к проверке")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # ✅ ЧЕКБОКС ДЛЯ АВТООБНОВЛЕНИЙ
        self.auto_update_checkbox = QCheckBox("🔄 Проверять обновления при запуске программы")
        self.auto_update_checkbox.setChecked(get_auto_update_enabled())
        self.auto_update_checkbox.setToolTip(
            "Если включено, программа будет автоматически проверять наличие обновлений при запуске.\n"
            "Вы всегда можете проверить обновления вручную через кнопку 'Обновить'."
        )
        self.auto_update_checkbox.stateChanged.connect(self.on_auto_update_toggled)
        layout.addWidget(self.auto_update_checkbox)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("⬇️ Проверить серверы")
        self.refresh_btn.clicked.connect(self.start_checks)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addSpacing(10)
        
        # ✅ ОБНОВЛЕННАЯ КНОПКА С ОЧИСТКОЙ КЭША
        self.update_btn = QPushButton("🔄 Проверить обновления")
        self.update_btn.setToolTip(
            "Принудительная проверка обновлений\n"
            "Игнорирует кэш и проверяет сервер напрямую"
        )
        self.update_btn.clicked.connect(self.check_updates)
        button_layout.addWidget(self.update_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def on_auto_update_toggled(self, state):
        """Обработчик изменения состояния чекбокса автообновлений"""
        enabled = self.auto_update_checkbox.isChecked()
        
        if set_auto_update_enabled(enabled):
            status = "включена" if enabled else "отключена"
            self.status_label.setText(f"✅ Автопроверка обновлений {status}")
            log(f"Автоматическая проверка обновлений {status}", "🔄 UPDATE")
        else:
            log("Ошибка сохранения настройки автообновлений", "❌ ERROR")
            # Возвращаем чекбокс в предыдущее состояние
            self.auto_update_checkbox.blockSignals(True)
            self.auto_update_checkbox.setChecked(not enabled)
            self.auto_update_checkbox.blockSignals(False)
            self.status_label.setText("❌ Ошибка сохранения настройки")

    def _create_versions_tab(self):
        """Создаёт вкладку версий"""
        layout = QVBoxLayout()
        
        # Группа Stable
        stable_group = QGroupBox("🔒 Стабильная версия (Stable)")
        stable_layout = QVBoxLayout()
        
        self.stable_version_label = QLabel("Проверка...")
        self.stable_version_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        stable_layout.addWidget(self.stable_version_label)
        
        self.stable_notes = QTextEdit()
        self.stable_notes.setReadOnly(True)
        self.stable_notes.setMaximumHeight(100)
        self.stable_notes.setPlaceholderText("Информация о релизе...")
        stable_layout.addWidget(self.stable_notes)
        
        self.stable_status = QLabel("")
        stable_layout.addWidget(self.stable_status)
        
        stable_group.setLayout(stable_layout)
        layout.addWidget(stable_group)
        
        # Группа Dev
        dev_group = QGroupBox("🚀 Версия для разработчиков (Dev)")
        dev_layout = QVBoxLayout()
        
        self.dev_version_label = QLabel("Проверка...")
        self.dev_version_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        dev_layout.addWidget(self.dev_version_label)
        
        self.dev_notes = QTextEdit()
        self.dev_notes.setReadOnly(True)
        self.dev_notes.setMaximumHeight(100)
        self.dev_notes.setPlaceholderText("Информация о релизе...")
        dev_layout.addWidget(self.dev_notes)
        
        self.dev_status = QLabel("")
        dev_layout.addWidget(self.dev_status)
        
        dev_group.setLayout(dev_layout)
        layout.addWidget(dev_group)
        
        # ✅ ДОБАВЛЯЕМ ИНФОРМАЦИЮ О КЭШЕ
        cache_group = QGroupBox("💾 Информация о кэше обновлений")
        cache_layout = QVBoxLayout()
        
        self.cache_info_label = QLabel("Проверка кэша...")
        self.cache_info_label.setWordWrap(True)
        self.cache_info_label.setStyleSheet("color: #666;")
        cache_layout.addWidget(self.cache_info_label)
        
        # Кнопка очистки кэша
        clear_cache_btn = QPushButton("🗑️ Очистить кэш")
        clear_cache_btn.setToolTip("Очистить кэш обновлений для принудительной проверки")
        clear_cache_btn.clicked.connect(self.clear_update_cache)
        clear_cache_btn.setFixedWidth(150)
        clear_cache_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        cache_layout.addWidget(clear_cache_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)
        
        layout.addStretch()
        
        self.versions_tab.setLayout(layout)
        
        # ✅ Обновляем информацию о кэше после создания UI
        QTimer.singleShot(200, self.update_cache_info)

    def _create_servers_tab(self):
        """Создаёт вкладку серверов"""
        layout = QVBoxLayout()
        
        # Таблица серверов
        self.servers_table = QTableWidget()
        self.servers_table.setColumnCount(4)
        self.servers_table.setHorizontalHeaderLabels([
            "Сервер", "Статус", "Время отклика", "Информация"
        ])
        
        # Настройка таблицы
        header = self.servers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.servers_table.setAlternatingRowColors(True)
        self.servers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.servers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.servers_table)
        
        # Описание
        info_label = QLabel(
            f"💡 Система автоматически выбирает наиболее быстрый доступный источник.\n\n"
            f"⭐ Звёздочка — текущий активный сервер\n"
            f"🚫 Сервера блокируются после нескольких ошибок подряд на день"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(info_label)
        
        self.servers_tab.setLayout(layout)

    def update_vps_block_info(self):
        """Обновляет информацию о блокировке VPS"""
        try:
            from .release_manager import get_vps_block_info
            
            info = get_vps_block_info()
            
            if info['blocked']:
                until_dt = info.get('until_dt')
                if until_dt:
                    remaining = info['until_ts'] - time.time()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    
                    text = (
                        f"🚫 VPS временно отключён до {until_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"⏳ Осталось: {hours}ч {minutes}мин\n"
                        f"💡 Обновления получаются через GitHub API"
                    )
                    
                    self.vps_block_info.setText(text)
                    self.vps_block_info.show()
                    
                    log(f"VPS заблокирован до {until_dt}, осталось {hours}ч {minutes}мин", "🚫 STATUS")
                else:
                    self.vps_block_info.hide()
            else:
                self.vps_block_info.hide()
                
        except Exception as e:
            log(f"Ошибка обновления информации о блокировке: {e}", "❌ ERROR")

    def _create_stats_tab(self):
        """Создаёт вкладку статистики"""
        layout = QVBoxLayout()
        
        # Таблица статистики
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels([
            "Сервер", "Успешных", "Неудачных", "Ср. время", "Последний успех"
        ])
        
        # Настройка таблицы
        header = self.stats_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.stats_table)
        
        # Кнопка очистки статистики
        clear_btn = QPushButton("🗑️ Очистить статистику")
        clear_btn.clicked.connect(self.clear_stats)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addStretch()
        
        self.stats_tab.setLayout(layout)

    def start_checks(self):
        """Запускает проверку серверов и версий"""
        # Проверяем, не запущена ли уже проверка
        if hasattr(self, '_checking') and self._checking:
            self.status_label.setText("⏳ Проверка уже выполняется...")
            return
        
        self._checking = True
        
        # ✅ ОБНОВЛЯЕМ ИНФОРМАЦИЮ О БЛОКИРОВКЕ VPS
        self.update_vps_block_info()
        
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)  # Неопределённый прогресс
        self.status_label.setText("🔄 Проверка серверов...")
        
        # Очищаем таблицу серверов
        self.servers_table.setRowCount(0)
        
        # Останавливаем предыдущие воркеры если они есть
        if self.server_worker and self.server_worker.isRunning():
            self.server_worker.terminate()
            self.server_worker.wait()
        
        if self.version_worker and self.version_worker.isRunning():
            self.version_worker.terminate()
            self.version_worker.wait()
        
        # Проверка серверов
        self.server_worker = ServerCheckWorker()
        self.server_worker.server_checked.connect(self.on_server_checked)
        self.server_worker.all_complete.connect(self.on_servers_complete)
        self.server_worker.start()
        
        # Запускаем проверку версий
        self.version_worker = VersionCheckWorker()
        self.version_worker.version_found.connect(self.on_version_found)
        self.version_worker.complete.connect(self.on_versions_complete)
        self.version_worker.start()
        
        # Обновляем статистику
        self.update_stats()
        
        # ✅ ОБНОВЛЯЕМ ИНФОРМАЦИЮ О КЭШЕ ПОСЛЕ НЕБОЛЬШОЙ ЗАДЕРЖКИ
        QTimer.singleShot(500, self.update_cache_info)

    def on_versions_complete(self):
        """Завершение проверки версий"""
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.refresh_btn.setEnabled(True)
        self.status_label.setText("✅ Проверка завершена")
        self._checking = False

    def on_server_checked(self, server_name: str, status: dict):
        """Обработчик проверки сервера"""
        row = self.servers_table.rowCount()
        self.servers_table.insertRow(row)
        
        # Имя сервера
        name_item = QTableWidgetItem(server_name)
        
        # ✅ ПОДСВЕТКА ТЕКУЩЕГО СЕРВЕРА
        if status.get('is_current'):
            name_item.setText(f"⭐ {server_name}")
            name_item.setForeground(QColor(61, 174, 233))  # Синий
        
        self.servers_table.setItem(row, 0, name_item)
        
        # Статус
        status_item = QTableWidgetItem()
        if status['status'] == 'online':
            status_item.setText("✅ Онлайн")
            status_item.setForeground(QColor(0, 200, 0))
        else:
            status_item.setText("❌ Недоступен")
            status_item.setForeground(QColor(200, 0, 0))
        self.servers_table.setItem(row, 1, status_item)
        
        # Время отклика
        if status.get('response_time'):
            time_text = f"{status['response_time']*1000:.0f} мс"
        else:
            time_text = "—"
        self.servers_table.setItem(row, 2, QTableWidgetItem(time_text))
        
        # Дополнительная информация
        extra_info = ""
        if server_name == 'GitHub API':
            if status.get('rate_limit') is not None:
                extra_info = f"Rate limit: {status['rate_limit']}/{status.get('rate_limit_max', 60)}"
                if status.get('reset_time'):
                    extra_info += f" (сброс: {status['reset_time'].strftime('%H:%M')})"
        elif status['status'] == 'online':
            if status.get('stable_version') and status.get('test_version'):
                extra_info = f"Stable: {status['stable_version']}, Test: {status['test_version']}"
            elif status.get('url'):
                extra_info = status['url']
        elif status.get('error'):
            extra_info = status['error'][:50]
        
        self.servers_table.setItem(row, 3, QTableWidgetItem(extra_info))
    
    def on_servers_complete(self):
        """Завершение проверки серверов"""
        self.status_label.setText("✅ Проверка серверов завершена")
    
    def on_version_found(self, channel: str, version_info: dict):
        """Обработчик найденной версии"""
        if 'error' in version_info:
            version_text = f"❌ Ошибка: {version_info['error']}"
            notes_text = ""
            status_text = ""
        else:
            version_text = f"Версия {version_info['version']}"
            notes_text = version_info.get('release_notes', '')[:200]
            
            # Добавляем источник
            source = version_info.get('source', 'неизвестен')
            version_text += f" (из: {source})"
            
            # Сравниваем с текущей версией
            from updater.update import compare_versions
            try:
                current = APP_VERSION
                remote = version_info['version']
                cmp = compare_versions(current, remote)
                
                if cmp < 0:
                    status_text = "🆕 Доступно обновление!"
                    status_color = "color: #27ae60; font-weight: bold;"
                elif cmp == 0:
                    status_text = "✅ У вас последняя версия"
                    status_color = "color: #3498db;"
                else:
                    status_text = "⚠️ У вас более новая версия"
                    status_color = "color: #e67e22;"
            except:
                status_text = ""
                status_color = ""
        
        if channel == 'stable':
            self.stable_version_label.setText(version_text)
            self.stable_notes.setPlainText(notes_text)
            if 'error' not in version_info:
                self.stable_status.setText(status_text)
                self.stable_status.setStyleSheet(status_color)
        else:
            self.dev_version_label.setText(version_text)
            self.dev_notes.setPlainText(notes_text)
            if 'error' not in version_info:
                self.dev_status.setText(status_text)
                self.dev_status.setStyleSheet(status_color)
    
    def update_stats(self):
        """Обновляет статистику"""
        from updater.release_manager import get_release_manager
        
        manager = get_release_manager()
        stats = manager.get_server_statistics()
        
        self.stats_table.setRowCount(0)
        
        for server_name, server_stats in stats.items():
            row = self.stats_table.rowCount()
            self.stats_table.insertRow(row)
            
            self.stats_table.setItem(row, 0, QTableWidgetItem(server_name))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(server_stats['successes'])))
            self.stats_table.setItem(row, 2, QTableWidgetItem(str(server_stats['failures'])))
            
            avg_time = server_stats.get('avg_response_time', 0)
            if avg_time > 0:
                time_text = f"{avg_time*1000:.0f} мс"
            else:
                time_text = "—"
            self.stats_table.setItem(row, 3, QTableWidgetItem(time_text))
            
            last_success = server_stats.get('last_success')
            if last_success:
                dt = datetime.fromtimestamp(last_success)
                time_text = dt.strftime('%d.%m %H:%M')
            else:
                time_text = "Никогда"
            self.stats_table.setItem(row, 4, QTableWidgetItem(time_text))
    
    def clear_stats(self):
        """Очищает статистику"""
        import os
        from updater.release_manager import STATS_FILE
        
        try:
            if os.path.exists(STATS_FILE):
                os.remove(STATS_FILE)
            self.stats_table.setRowCount(0)
            self.status_label.setText("📊 Статистика очищена")
            log("Статистика серверов очищена", "🗑️ STATS")
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка: {e}")
            log(f"Ошибка очистки статистики: {e}", "❌ ERROR")
    
    def update_cache_info(self):
        """Обновляет информацию о кэше обновлений"""
        try:
            from updater import get_cache_info
            from config import CHANNEL
            
            log(f"🔍 Обновление информации о кэше для канала: {CHANNEL}", "DEBUG")
            
            cache_info = get_cache_info(CHANNEL)
            
            if cache_info and cache_info.get('version'):
                age_min = cache_info['age_minutes']
                age_hours = cache_info['age_hours']
                is_valid = cache_info['is_valid']
                version = cache_info['version']
                source = cache_info.get('source', 'неизвестно')
                
                # Форматируем возраст
                if age_min < 1:
                    age_str = "только что"
                elif age_min < 60:
                    age_str = f"{age_min} мин назад"
                else:
                    age_str = f"{age_hours} ч назад"
                
                # Форматируем статус
                if is_valid:
                    status_icon = "✅"
                    status_text = "актуален"
                    color = "#27ae60"
                else:
                    status_icon = "⏰"
                    status_text = "устарел"
                    color = "#e67e22"
                
                channel_name = "Test/Dev" if CHANNEL == "dev" else "Stable"
                
                info_text = (
                    f"{status_icon} Кэш {status_text} (обновлено {age_str})\n"
                    f"Канал: {channel_name}\n"
                    f"Версия: {version}\n"
                    f"Источник: {source}"
                )
                
                self.cache_info_label.setText(info_text)
                self.cache_info_label.setStyleSheet(f"color: {color};")
                
                log(f"✅ Отображен кэш: {channel_name} v{version} ({age_min} мин, источник: {source})", "🔄 CACHE")
            else:
                channel_name = "Test/Dev" if CHANNEL == "dev" else "Stable"
                self.cache_info_label.setText(
                    f"💾 Кэш для канала {channel_name} пуст.\n"
                    f"Информация будет сохранена после проверки."
                )
                self.cache_info_label.setStyleSheet("color: #888;")
                log(f"⚠️ Кэш пуст для канала {CHANNEL}", "🔄 CACHE")
                
        except Exception as e:
            self.cache_info_label.setText(f"⚠️ Ошибка чтения кэша: {str(e)[:50]}")
            self.cache_info_label.setStyleSheet("color: #e74c3c;")
            log(f"❌ Ошибка update_cache_info: {e}", "❌ ERROR")
            
            import traceback
            log(f"Traceback:\n{traceback.format_exc()}", "DEBUG")
    
    def clear_update_cache(self):
        """Очищает кэш обновлений"""
        try:
            from updater import invalidate_cache
            
            invalidate_cache(CHANNEL)
            
            self.update_cache_info()
            self.status_label.setText("🗑️ Кэш обновлений очищен")
            log(f"Кэш обновлений для канала {CHANNEL} очищен вручную", "🔄 CACHE")
            
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка очистки кэша: {e}")
            log(f"Ошибка очистки кэша: {e}", "❌ ERROR")
    
    def check_updates(self):
        """Запускает принудительную проверку обновлений (без кэша)"""
        try:
            from updater import invalidate_cache
            
            log("Запуск принудительной проверки обновлений из диалога", "🔄 UPDATE")
            
            # Очищаем кэш
            invalidate_cache(CHANNEL)
            self.status_label.setText("🔄 Кэш очищен, проверка обновлений...")
            
            # Блокируем кнопку на время проверки
            self.update_btn.setEnabled(False)
            self.update_btn.setText("⏳ Проверка...")
            
            # Эмитим сигнал для запуска обновления в main.py
            self.update_requested.emit()
            
            # Закрываем диалог
            self.close()
            
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка: {e}")
            log(f"Ошибка при запуске обновления: {e}", "❌ ERROR")
            
            # Разблокируем кнопку в случае ошибки
            self.update_btn.setEnabled(True)
            self.update_btn.setText("🔄 Проверить обновления")