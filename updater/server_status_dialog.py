"""
Диалог показа статуса серверов обновлений и последних версий
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QTableWidgetItem,
                            QGroupBox, QProgressBar, QTabWidget, QWidget,
                            QHeaderView, QTextEdit, QCheckBox, QFrame,
                            QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QIcon
import os
from datetime import datetime
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
        
        # ✅ ФИКСИРУЕМ текущий сервер в НАЧАЛЕ проверки
        # чтобы он не менялся во время проверки (при переключении)
        current_server_id = pool.selected_server['id']
        
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
                    'is_current': server_id == current_server_id,  # ✅ Используем сохранённый ID
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
                        'is_current': server_id == current_server_id,  # ✅ Используем сохранённый ID
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
                        'is_current': server_id == current_server_id,  # ✅ Используем сохранённый ID
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
                    'is_current': server_id == current_server_id,  # ✅ Используем сохранённый ID
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
    """Диалог статуса серверов - компактный без лишнего пространства"""
    
    update_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Статус серверов обновлений")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        # Иконка
        icon_path = ICON_TEST_PATH if CHANNEL == "test" else ICON_PATH
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.server_worker = None
        self.version_worker = None
        
        self._build_ui()
        
        # Обеспечиваем адекватный стартовый размер
        self._ensure_initial_size()
        
        QTimer.singleShot(100, self.start_checks)
    
    def _build_ui(self):
        """Строит компактный UI с вкладками"""
        main = QVBoxLayout(self)
        main.setSpacing(10)
        main.setContentsMargins(12, 10, 12, 10)
        
        # === Header ===
        header_box = QVBoxLayout()
        header_box.setSpacing(0)
        
        title = QLabel("Мониторинг серверов обновлений Zapret")
        title.setStyleSheet("font-weight: 600; font-size: 13pt;")
        header_box.addWidget(title)
        
        subtitle = QLabel(f"Версия: {APP_VERSION} · Канал: {CHANNEL}")
        subtitle.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        header_box.addWidget(subtitle)
        
        main.addLayout(header_box)
        
        # === Вкладки с контентом ===
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabs.addTab(self._build_servers_tab(), "Сервера")
        self.tabs.addTab(self._build_versions_tab(), "Версии")
        self.tabs.addTab(self._build_stats_tab(), "Статистика")
        self.tabs.setMinimumHeight(320)
        main.addWidget(self.tabs, 1)
        
        # === Прогресс / статус ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        main.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Готово к проверке")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d;")
        main.addWidget(self.status_label)
        
        # === Нижняя панель управления ===
        controls = QHBoxLayout()
        controls.setSpacing(8)
        
        self.auto_update_checkbox = QCheckBox("Проверять обновления при запуске")
        self.auto_update_checkbox.setChecked(get_auto_update_enabled())
        self.auto_update_checkbox.stateChanged.connect(self.on_auto_update_toggled)
        controls.addWidget(self.auto_update_checkbox)
        
        controls.addStretch()
        
        self.refresh_btn = QPushButton("Проверить серверы")
        self.refresh_btn.clicked.connect(self.start_checks)
        controls.addWidget(self.refresh_btn)
        
        self.update_btn = QPushButton("Проверить обновления")
        self.update_btn.clicked.connect(self.check_updates)
        controls.addWidget(self.update_btn)
        
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.close)
        controls.addWidget(self.close_btn)
        
        main.addLayout(controls)
        
        QTimer.singleShot(200, self.update_cache_info)

    def _ensure_initial_size(self):
        """Фиксирует минимальный размер по реальному контенту"""
        hint = self.minimumSizeHint()
        min_width = max(780, hint.width())
        min_height = max(540, hint.height())
        self.setMinimumSize(min_width, min_height)
        self.resize(min_width, min_height)
    
    def _build_servers_tab(self) -> QWidget:
        """Создаёт вкладку серверов"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        
        self.vps_block_info = QLabel()
        self.vps_block_info.setWordWrap(True)
        self.vps_block_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.vps_block_info.setStyleSheet(
            "background: #fdecea; border: 1px solid #f5c6cb; color: #c0392b; "
            "border-radius: 4px; padding: 6px; font-size: 9pt;"
        )
        self.vps_block_info.hide()
        layout.addWidget(self.vps_block_info)
        
        layout.addWidget(self._create_servers_section(), 1)
        return tab
    
    def _build_versions_tab(self) -> QWidget:
        """Создаёт вкладку версий и кэша"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        
        layout.addWidget(self._create_versions_section(), 1)
        layout.addWidget(self._create_cache_section())
        return tab
    
    def _build_stats_tab(self) -> QWidget:
        """Создаёт вкладку статистики"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        
        layout.addWidget(self._create_stats_section(), 1)
        return tab
    
    def _create_servers_section(self) -> QGroupBox:
        """Создаёт компактный блок с таблицей серверов"""
        group = QGroupBox("Сервера обновлений")
        group.setStyleSheet("QGroupBox { font-weight: 600; }")
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        
        self.servers_table = QTableWidget(0, 4)
        self.servers_table.setHorizontalHeaderLabels(["Сервер", "Статус", "Время", "Инфо"])
        header = self.servers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.servers_table.verticalHeader().setVisible(False)
        self.servers_table.verticalHeader().setDefaultSectionSize(22)
        self.servers_table.setAlternatingRowColors(True)
        self.servers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.servers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.servers_table)
        
        hint = QLabel("⭐ активный  🚫 блокирован после ошибок")
        hint.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        layout.addWidget(hint)
        
        return group
    
    def _create_version_card(self, title: str):
        """Унифицированная карточка для информации о релизе"""
        card = QFrame()
        card.setObjectName("versionCard")
        card.setStyleSheet("""
            QFrame#versionCard {
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                background: rgba(255,255,255,0.02);
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 10pt;")
        header.addWidget(title_label)
        
        status_label = QLabel("")
        status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_label.setStyleSheet("font-size: 9pt;")
        header.addWidget(status_label)
        layout.addLayout(header)
        
        version_label = QLabel("Версия: —")
        version_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(version_label)
        
        source_label = QLabel("Источник: —")
        source_label.setWordWrap(True)
        source_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(source_label)
        
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setMinimumHeight(52)
        notes.setMaximumHeight(90)
        notes.setPlaceholderText("Заметки релиза...")
        notes.setStyleSheet("""
            QTextEdit {
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 4px;
                background: rgba(0,0,0,0.05);
                font-size: 9pt;
            }
        """)
        layout.addWidget(notes)
        
        return card, version_label, source_label, status_label, notes
    
    def _create_versions_section(self) -> QGroupBox:
        """Блок со сводкой версий"""
        group = QGroupBox("Версии Zapret")
        group.setStyleSheet("QGroupBox { font-weight: 600; }")
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        
        stable_card, self.stable_version_label, self.stable_source_label, self.stable_status, self.stable_notes = self._create_version_card("🔒 Stable")
        layout.addWidget(stable_card)
        
        dev_card, self.dev_version_label, self.dev_source_label, self.dev_status, self.dev_notes = self._create_version_card("🚀 Dev")
        layout.addWidget(dev_card)
        
        return group
    
    def _create_cache_section(self) -> QGroupBox:
        """Блок информации о кэше и действиях"""
        group = QGroupBox("Кэш обновлений")
        group.setStyleSheet("QGroupBox { font-weight: 600; }")
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        
        self.cache_info_label = QLabel("💾 Кэш: проверка...")
        self.cache_info_label.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        self.cache_info_label.setWordWrap(True)
        layout.addWidget(self.cache_info_label)
        
        actions = QHBoxLayout()
        actions.addStretch()
        clear_btn = QPushButton("Очистить кэш")
        clear_btn.clicked.connect(self.clear_update_cache)
        actions.addWidget(clear_btn)
        layout.addLayout(actions)
        
        return group
    
    def _create_stats_section(self) -> QGroupBox:
        """Блок с статистикой серверов"""
        group = QGroupBox("Статистика опросов")
        group.setStyleSheet("QGroupBox { font-weight: 600; }")
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        
        self.stats_table = QTableWidget(0, 5)
        self.stats_table.setHorizontalHeaderLabels(["Сервер", "OK", "Fail", "Время", "Послед."])
        header = self.stats_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.verticalHeader().setDefaultSectionSize(20)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.stats_table)
        
        controls = QHBoxLayout()
        controls.addStretch()
        clear_btn = QPushButton("Очистить статистику")
        clear_btn.clicked.connect(self.clear_stats)
        controls.addWidget(clear_btn)
        layout.addLayout(controls)
        
        return group
    
    def on_auto_update_toggled(self, _state):
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
        error = version_info.get('error')
        notes_text = ""
        status_text = ""
        status_color = ""
        source_text = ""
        version_text = "Версия: —"
        
        if error:
            version_text = "Версия: недоступна"
            source_text = f"Ошибка: {error}"
            status_text = "⚠️ Ошибка получения"
            status_color = "color: #e74c3c;"
        else:
            version = version_info.get('version', 'н/д')
            version_text = f"Версия {version}"
            source = version_info.get('source') or version_info.get('server_name') or "неизвестно"
            source_text = f"Источник: {source}"
            notes_text = (version_info.get('release_notes') or '')[:400].strip()
            
            from updater.update import compare_versions
            try:
                cmp = compare_versions(APP_VERSION, version)
                if cmp < 0:
                    status_text = "🆕 Доступно обновление"
                    status_color = "color: #27ae60; font-weight: bold;"
                elif cmp == 0:
                    status_text = "✅ У вас последняя версия"
                    status_color = "color: #3498db;"
                else:
                    status_text = "⚠️ У вас более новая версия"
                    status_color = "color: #e67e22;"
            except Exception:
                status_text = ""
                status_color = ""
        
        if channel == 'stable':
            self.stable_version_label.setText(version_text)
            self.stable_source_label.setText(source_text)
            self.stable_notes.setPlainText(notes_text)
            self.stable_status.setText(status_text)
            self.stable_status.setStyleSheet(status_color)
        else:
            self.dev_version_label.setText(version_text)
            self.dev_source_label.setText(source_text)
            self.dev_notes.setPlainText(notes_text)
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
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(server_stats.get('successes', 0))))
            self.stats_table.setItem(row, 2, QTableWidgetItem(str(server_stats.get('failures', 0))))
            
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