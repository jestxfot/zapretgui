# connection_test.py

import os
import subprocess
import logging
import requests, webbrowser
from datetime import datetime
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QComboBox, QTextEdit, QMessageBox, QHBoxLayout, QFrame
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from utils import run_hidden # Импортируем нашу обертку для subprocess
from config import APP_VERSION, LOGS_FOLDER  # Добавляем импорт
from strategy_checker import StrategyChecker  # Добавляем импорт
from dns_checker import DNSChecker
from dns_check_dialog import DNSCheckDialog

from tgram.tg_log_bot import send_log_file, check_bot_connection
from tgram.tg_log_delta import get_client_id
import platform

class ConnectionTestWorker(QObject):
    """Рабочий поток для выполнения тестов соединения."""
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, test_type="all"):
        super().__init__()
        self.test_type = test_type
        
        # ✅ ИСПРАВЛЕНИЕ: Создаем лог-файл в папке logs
        os.makedirs(LOGS_FOLDER, exist_ok=True)
        self.log_filename = os.path.join(LOGS_FOLDER, "connection_test_temp.log")
        
        # ✅ ДОБАВЛЯЕМ ФЛАГ ДЛЯ МЯГКОЙ ОСТАНОВКИ
        self._stop_requested = False
        
        # Настройка логгирования с явным указанием кодировки
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        logging.basicConfig(
            filename=self.log_filename,
            level=logging.INFO,
            format="%(asctime)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            encoding='utf-8'  # Добавляем явную кодировку
        )
    
        file_handler = logging.FileHandler(self.log_filename, 'w', 'utf-8')
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S"))
        logging.getLogger().handlers = [file_handler]
    
    def stop_gracefully(self):
        """✅ Мягкая остановка теста"""
        self._stop_requested = True
        self.log_message("⚠️ Получен запрос на остановку теста...")
    
    def is_stop_requested(self):
        """Проверяет, запрошена ли остановка"""
        return self._stop_requested
    
    def log_message(self, message):
        """Записывает сообщение в лог и отправляет сигнал в GUI."""
        if not self._stop_requested:  # Не логируем после остановки
            logging.info(message)
            self.update_signal.emit(message)

    def check_dns_poisoning(self):
        """Проверяет DNS подмену провайдером"""
        if self.is_stop_requested():
            return
        
        self.log_message("")
        self.log_message("=" * 40)
        self.log_message("🔍 ПРОВЕРКА DNS ПОДМЕНЫ ПРОВАЙДЕРОМ")
        self.log_message("=" * 40)
        
        try:
            dns_checker = DNSChecker()
            results = dns_checker.check_dns_poisoning(log_callback=self.log_message)
            
            # Добавляем итоговые рекомендации
            if results['summary']['dns_poisoning_detected']:
                self.log_message("")
                self.log_message("⚠️ ДЕЙСТВИЯ ДЛЯ ИСПРАВЛЕНИЯ:")
                self.log_message("1. Смените DNS в настройках сетевого адаптера:")
                self.log_message("   • Откройте: Панель управления → Сеть и Интернет")
                self.log_message("   • Измените настройки адаптера → Свойства")
                self.log_message("   • TCP/IPv4 → Свойства → Использовать следующие DNS:")
                
                if results['summary']['recommended_dns']:
                    dns_ip = dns_checker.dns_servers.get(results['summary']['recommended_dns'])
                    if dns_ip:
                        self.log_message(f"   • Предпочитаемый: {dns_ip}")
                        self.log_message(f"   • Альтернативный: 8.8.4.4")
                else:
                    self.log_message("   • Предпочитаемый: 8.8.8.8 (Google)")
                    self.log_message("   • Альтернативный: 1.1.1.1 (Cloudflare)")
                
                self.log_message("")
                self.log_message("2. После смены DNS перезапустите Zapret")
                self.log_message("3. Очистите кэш DNS командой: ipconfig /flushdns")
            
        except Exception as e:
            self.log_message(f"❌ Ошибка проверки DNS: {e}")
        
        self.log_message("")

    def ping(self, host, count=4):
        """Выполняет ping с возможностью прерывания."""
        if self.is_stop_requested():
            return False
            
        try:
            self.log_message(f"Проверка доступности для URL: {host}")
            
            # Используем run_hidden напрямую
            command = ["ping", "-n", str(count), host]
            
            # ✅ ИСПРАВЛЕНИЕ: Используем subprocess напрямую для лучшего контроля
            try:
                # Для Windows используем shell=False и правильную кодировку
                result = subprocess.run(
                    command,
                    capture_output=True,
                    timeout=10,
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            except Exception as e:
                self.log_message(f"Ошибка выполнения ping: {e}")
                return False
            
            if self.is_stop_requested():
                return False
            
            # ✅ ИСПРАВЛЕНИЕ: Пробуем разные кодировки для декодирования
            output = ""
            if result and result.stdout:
                # Пробуем разные кодировки Windows
                for encoding in ['cp866', 'cp1251', 'utf-8', 'latin-1']:
                    try:
                        output = result.stdout.decode(encoding)
                        break
                    except:
                        continue
                
                # Если не удалось декодировать, используем ignore
                if not output:
                    output = result.stdout.decode('utf-8', errors='ignore')
            
            # ✅ ОТЛАДКА: Логируем первые 200 символов вывода для диагностики
            if output:
                debug_output = output[:200].replace('\n', ' ').replace('\r', '')
                self.log_message(f"[DEBUG] Ping output sample: {debug_output}")
            
            # ✅ УЛУЧШЕННЫЙ ПАРСИНГ: Более универсальные паттерны
            # Английские паттерны
            en_success_patterns = [
                "bytes=", "Bytes=", "BYTES=",
                "time=", "Time=", "TIME=",
                "TTL=", "ttl=", "Ttl="
            ]
            
            # Русские паттерны
            ru_success_patterns = [
                "байт=", "Байт=", "БАЙТ=",
                "время=", "Время=", "ВРЕМЯ=",
                "TTL=", "ttl=", "Ttl="
            ]
            
            # Паттерны ошибок
            fail_patterns = [
                # Английские
                "unreachable", "timed out", "could not find", 
                "100% loss", "Destination host unreachable",
                "Request timed out", "100% packet loss",
                "General failure", "Transmit failed",
                # Русские
                "недоступен", "превышен", "не удается",
                "100% потерь", "Заданный узел недоступен",
                "Превышен интервал", "100% потери",
                "Общий сбой", "Сбой передачи"
            ]
            
            # Проверяем на успешность - ищем любой из паттернов успеха
            success_count = 0
            found_success = False
            
            # Сначала проверяем английские паттерны
            for pattern in en_success_patterns:
                if pattern in output:
                    success_count = output.count(pattern)
                    found_success = True
                    break
            
            # Если не нашли, проверяем русские
            if not found_success:
                for pattern in ru_success_patterns:
                    if pattern in output:
                        success_count = output.count(pattern)
                        found_success = True
                        break
            
            # Проверяем на ошибки
            is_failed = any(pattern.lower() in output.lower() for pattern in fail_patterns)
            
            # ✅ ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: Ищем статистику пакетов
            # Английская статистика: "Packets: Sent = 4, Received = 4"
            # Русская статистика: "Пакетов: отправлено = 4, получено = 4"
            
            # Паттерн для английской версии
            import re
            en_stats = re.search(r'Packets:\s*Sent\s*=\s*(\d+),\s*Received\s*=\s*(\d+)', output, re.IGNORECASE)
            ru_stats = re.search(r'Пакетов:\s*отправлено\s*=\s*(\d+),\s*получено\s*=\s*(\d+)', output, re.IGNORECASE)
            
            if en_stats:
                sent = int(en_stats.group(1))
                received = int(en_stats.group(2))
                if received > 0:
                    success_count = received
                    found_success = True
                self.log_message(f"{host}: Отправлено: {sent}, Получено: {received}")
            elif ru_stats:
                sent = int(ru_stats.group(1))
                received = int(ru_stats.group(2))
                if received > 0:
                    success_count = received
                    found_success = True
                self.log_message(f"{host}: Отправлено: {sent}, Получено: {received}")
            elif found_success and success_count > 0:
                self.log_message(f"{host}: Отправлено: {count}, Получено: {success_count}")
            elif is_failed:
                self.log_message(f"{host}: Отправлено: {count}, Получено: 0")
            else:
                # Если ничего не нашли, пытаемся найти хотя бы IP адрес в выводе
                ip_pattern = re.search(r'?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?', output)
                if ip_pattern:
                    # Если нашли IP, значит хост разрешился
                    self.log_message(f"{host}: DNS разрешен в {ip_pattern.group(1)}, статус пинга неизвестен")
                else:
                    self.log_message(f"{host}: Отправлено: {count}, Статус неизвестен")
            
            # Выводим детали если пинг успешен
            if found_success and success_count > 0:
                # Парсим время отклика
                latency_found = False
                
                # Пробуем найти время отклика
                for line in output.splitlines():
                    # Английские варианты
                    if "time=" in line or "Time=" in line:
                        match = re.search(r'time[<=](\d+)ms', line, re.IGNORECASE)
                        if match:
                            ms = match.group(1)
                            self.log_message(f"\tДоступен (Latency: {ms}ms)")
                            latency_found = True
                            break
                        # Альтернативный формат time<1ms
                        elif "time<" in line:
                            self.log_message(f"\tДоступен (Latency: <1ms)")
                            latency_found = True
                            break
                    
                    # Русские варианты
                    elif "время=" in line or "Время=" in line:
                        match = re.search(r'время[<=](\d+)', line, re.IGNORECASE)
                        if match:
                            ms = match.group(1)
                            self.log_message(f"\tДоступен (Latency: {ms}ms)")
                            latency_found = True
                            break
                
                if not latency_found:
                    self.log_message(f"\tДоступен")
            elif is_failed:
                # Определяем тип ошибки
                if any(x in output.lower() for x in ["could not find", "не удается"]):
                    self.log_message(f"\tНедоступен (DNS не разрешается)")
                elif any(x in output.lower() for x in ["unreachable", "недоступен"]):
                    self.log_message(f"\tНедоступен (узел недоступен)")
                elif any(x in output.lower() for x in ["timed out", "превышен"]):
                    self.log_message(f"\tНедоступен (таймаут)")
                else:
                    self.log_message(f"\tНедоступен")
            else:
                self.log_message(f"\tСтатус неопределен")
                
            return True
            
        except subprocess.TimeoutExpired:
            if not self.is_stop_requested():
                self.log_message(f"Таймаут при проверке {host}")
            return False
        except Exception as e:
            if not self.is_stop_requested():
                self.log_message(f"Ошибка при проверке {host}: {str(e)}")
            return False
    
    def check_discord(self):
        """Проверяет доступность Discord с проверкой остановки."""
        if self.is_stop_requested():
            return
            
        self.log_message("Запуск проверки доступности Discord:")
        
        if not self.is_stop_requested():
            self.ping("discord.com")
            
        if not self.is_stop_requested():
            self.log_message("")
            self.log_message("Проверка доступности Discord завершена.")

    def check_youtube(self):
        """Проверяет доступность YouTube с проверкой остановки."""
        if self.is_stop_requested():
            return
            
        youtube_ips = [
            "212.188.49.81",
            "74.125.168.135", 
            "173.194.140.136",
            "172.217.131.103"
        ]
        
        youtube_addresses = [
            "rr6.sn-jvhnu5g-n8v6.googlevideo.com",
            "rr4---sn-jvhnu5g-c35z.googlevideo.com",
            "rr4---sn-jvhnu5g-n8ve7.googlevideo.com",
            "rr2---sn-aigl6nze.googlevideo.com",
            "rr7---sn-jvhnu5g-c35e.googlevideo.com",
            "rr3---sn-jvhnu5g-c35d.googlevideo.com",
            "rr3---sn-q4fl6n6r.googlevideo.com",
            "rr2---sn-axq7sn7z.googlevideo.com"
        ]
        
        curl_test_domains = [
            "rr2---sn-axq7sn7z.googlevideo.com",
            "rr1---sn-axq7sn7z.googlevideo.com", 
            "rr3---sn-axq7sn7z.googlevideo.com"
        ]
        
        self.log_message("Запуск проверки доступности YouTube:")

        # Добавляем DNS проверку ПЕРЕД основными тестами
        if not self.is_stop_requested():
            self.check_dns_poisoning()

        if not self.is_stop_requested():
            self.ping("www.youtube.com")

        if not self.is_stop_requested():
            self.log_message("")
            self.log_message("=" * 40)
            self.log_message("Проверка поддоменов googlevideo.com через curl:")
            self.log_message("=" * 40)
                    
        # Проверка поддоменов через curl
        for domain in curl_test_domains:
            if self.is_stop_requested():
                break
            self.check_curl_domain(domain)
        
        # Остальные проверки с аналогичными проверками остановки
        if not self.is_stop_requested():
            self.check_curl_extended()

        if not self.is_stop_requested():
            self.check_youtube_video_access()
        
        if not self.is_stop_requested():
            self.check_zapret_status()
        
        if not self.is_stop_requested():
            self.interpret_youtube_results()
                
        # Проверка IP-адресов через ping
        for ip in youtube_ips:
            if self.is_stop_requested():
                break
            self.log_message(f"Проверка доступности для IP: {ip}")
            self.ping(ip)
        
        # Проверка стандартных поддоменов через ping
        for address in youtube_addresses:
            if self.is_stop_requested():
                break
            self.ping(address)
                
        if not self.is_stop_requested():
            self.log_message("")
            self.log_message("Проверка доступности YouTube завершена.")
            self.log_message(f"Лог сохранён в файле {os.path.abspath(self.log_filename)}")


    def check_youtube_video_access(self):
        """Проверяет реальный доступ к YouTube видео"""
        self.log_message("=" * 40)
        self.log_message("Проверка реального доступа к YouTube видео:")
        self.log_message("=" * 40)
        
        # Тестовые видео URL с реальными параметрами
        test_video_urls = [
            "https://rr2---sn-axq7sn7z.googlevideo.com/generate_204",  # Endpoint для проверки
            "https://www.googleapis.com/youtube/v3/videos?id=dQw4w9WgXcQ&key=test",  # API endpoint
            "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg"  # Thumbnail сервер
        ]
        
        for url in test_video_urls:
            self.check_real_youtube_endpoint(url)

    def check_real_youtube_endpoint(self, url):
        """Проверяет реальный YouTube endpoint"""
        try:
            domain = url.split('/')[2]  # Извлекаем домен
            path = '/' + '/'.join(url.split('/')[3:])  # Извлекаем путь
            
            self.log_message(f"Тест реального endpoint: {domain}{path}")
            
            # ✅ ИСПРАВЛЕНИЕ: Ищем curl в разных местах
            curl_paths = [
                "C:\\Windows\\System32\\curl.exe",
                "C:\\Windows\\SysWOW64\\curl.exe",
                "curl.exe",
                "curl"
            ]
            
            curl_exe = None
            for path in curl_paths:
                try:
                    test_cmd = [path, "--version"]
                    test_result = subprocess.run(test_cmd, capture_output=True, timeout=2, 
                                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    if test_result.returncode == 0:
                        curl_exe = path
                        break
                except:
                    continue
            
            if not curl_exe:
                self.log_message(f"  ⚠️ curl не найден, пропускаем тест")
                return
            
            command = [
                curl_exe, "-I",
                "--connect-timeout", "5",
                "--max-time", "10", 
                "--silent", "--show-error",
                url
            ]
            
            result = subprocess.run(command, capture_output=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            # ✅ ИСПРАВЛЕНИЕ: Правильно обрабатываем stdout
            if result and result.returncode == 0:
                output = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
                    
                lines = output.strip().split('\n') if output else []
                status_line = lines[0] if lines else ""
                
                if "HTTP/" in status_line:
                    status_code = status_line.split()[1] if len(status_line.split()) > 1 else "???"
                    if status_code in ['200', '204']:  # Успешные коды
                        self.log_message(f"  ✅ Реальный YouTube endpoint работает (HTTP {status_code})")
                    elif status_code == '404':
                        self.log_message(f"  ⚠️ Endpoint не найден, но сервер доступен (HTTP {status_code})")
                    elif status_code in ['403', '429']:
                        self.log_message(f"  🚫 YouTube блокирует запрос (HTTP {status_code})")
                    else:
                        self.log_message(f"  ❓ Неожиданный ответ (HTTP {status_code})")
                else:
                    self.log_message(f"  ❌ Не удалось получить HTTP статус")
            else:
                error_output = result.stderr.decode('utf-8', errors='ignore') if result and result.stderr else ""
                        
                if "could not resolve host" in error_output.lower():
                    self.log_message(f"  ❌ DNS блокировка")
                elif "connection timed out" in error_output.lower():
                    self.log_message(f"  ❌ Таймаут - возможная DPI блокировка")
                elif "connection refused" in error_output.lower():
                    self.log_message(f"  ❌ Соединение отклонено - блокировка")
                else:
                    self.log_message(f"  ❌ Ошибка соединения")
                    
        except Exception as e:
            self.log_message(f"  ❌ Ошибка теста: {str(e)}")

    def interpret_youtube_results(self):
        """Интерпретирует результаты YouTube тестов"""
        self.log_message("=" * 40)
        self.log_message("🔍 АНАЛИЗ РЕЗУЛЬТАТОВ:")
        self.log_message("=" * 40)
        
        # Проверяем наличие SSL handshake проблем в логе
        ssl_problems = self._check_ssl_handshake_issues()
        
        if ssl_problems:
            self.log_message("🚨 ОБНАРУЖЕНА DPI БЛОКИРОВКА!")
            self.log_message("")
            self.log_message("❌ Признаки блокировки:")
            self.log_message("   • SSL handshake timeout на googlevideo.com")
            self.log_message("   • TCP соединение работает, но TLS блокируется")
            self.log_message("   • DPI система активна и блокирует HTTPS")
            self.log_message("")
            self.log_message("🛠️ ТРЕБУЕТСЯ ЗАПУСК ZAPRET:")
            self.log_message("   1. ✅ Убедитесь что Zapret запущен")
            self.log_message("   2. ✅ Проверьте что выбрана рабочая стратегия")
            self.log_message("   3. ✅ Дождитесь полной инициализации Zapret")
            self.log_message("   4. ✅ Повторите тест через 30-60 секунд")
            self.log_message("")
            self.log_message("⚠️ БЕЗ ZAPRET YOUTUBE НЕ БУДЕТ РАБОТАТЬ!")
            
        else:
            self.log_message("🎉 ОТЛИЧНЫЕ НОВОСТИ!")
            self.log_message("✅ YouTube полностью разблокирован и должен работать!")
            self.log_message("")
            self.log_message("🔑 Ключевые индикаторы успеха:")
            self.log_message("   • HTTP 204 на /generate_204 - идеальный ответ")
            self.log_message("   • HTTP 200 на thumbnail сервер - изображения загружаются")  
            self.log_message("   • SSL handshake успешен - нет DPI блокировки")
            self.log_message("   • DNS разрешается - нет DNS блокировки")
            
        self.log_message("")
        self.log_message("📋 Справочная информация:")
        self.log_message("   • HTTP 404 на корневых путях CDN - НОРМАЛЬНО")
        self.log_message("   • Ping успешный = сетевая связность OK")
        self.log_message("   • Порт 443 открыт = TCP соединение OK")
        self.log_message("   • SSL handshake = критичен для HTTPS")


    def _check_ssl_handshake_issues(self):
        """Проверяет наличие проблем с SSL handshake в результатах"""
        try:
            # Проверяем текущие результаты теста
            # Это упрощенная проверка - в реальности можно анализировать self.result_text
            
            # Читаем лог-файл для анализа
            if os.path.exists(self.log_filename):
                with open(self.log_filename, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    
                # Ищем признаки SSL проблем
                ssl_timeout_count = log_content.count("SSL handshake неудачен")
                ssl_error_count = log_content.count("Проблема с SSL/сертификатом")
                
                # Если больше 3 SSL ошибок - значит проблема системная
                return ssl_timeout_count >= 3 or ssl_error_count >= 3
                
        except Exception:
            pass
        
        return False

    def check_zapret_status(self):
        """Проверяет статус Zapret"""
        self.log_message("=" * 40)
        self.log_message("🔍 ПРОВЕРКА СТАТУСА ZAPRET:")
        self.log_message("=" * 40)
        
        try:
            # Проверяем процесс winws.exe
            command = ["tasklist", "/FI", "IMAGENAME eq winws.exe", "/FO", "CSV"]
            
            # ✅ ИСПРАВЛЕНИЕ: Используем subprocess напрямую с правильными параметрами
            result = subprocess.run(command, capture_output=True, text=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            # ✅ ИСПРАВЛЕНИЕ: Правильно обрабатываем stdout
            if result and result.stdout:
                output = result.stdout
                    
                if "winws.exe" in output:
                    self.log_message("✅ Процесс winws.exe запущен")
                    
                    # Извлекаем PID и память
                    lines = output.strip().split('\n')
                    for line in lines[1:]:  # Пропускаем заголовок
                        if 'winws.exe' in line:
                            parts = line.split(',')
                            if len(parts) >= 2:
                                pid = parts[1].strip('"')
                                memory = parts[4].strip('"') if len(parts) > 4 else "N/A"
                                self.log_message(f"   PID: {pid}, Память: {memory}")
                else:
                    self.log_message("❌ Процесс winws.exe НЕ запущен")
                    self.log_message("   Zapret не работает!")
            else:
                self.log_message("❌ Не удалось проверить процесс winws.exe")
            
            # ДОБАВЛЯЕМ проверку выбранной стратегии
            self.check_current_strategy()
                
        except Exception as e:
            self.log_message(f"❌ Ошибка проверки Zapret: {e}")
            
        self.log_message("")

    def check_current_strategy(self):
        """Проверяет и выводит информацию о текущей выбранной стратегии"""
        try:
            # Используем новый StrategyChecker
            checker = StrategyChecker()
            strategy_info = checker.check_current_strategy()
            
            # Форматируем и выводим информацию
            info_lines = checker.format_strategy_info(strategy_info)
            for line in info_lines:
                self.log_message(line)
            
            # Дополнительно проверяем настройки автозапуска
            self._check_autostart_settings()
            
        except Exception as e:
            self.log_message(f"❌ Ошибка при проверке стратегии: {e}")

    def _check_autostart_settings(self):
        """Проверяет настройки автозапуска"""
        try:
            from config import get_dpi_autostart, get_strategy_autoload
            
            self.log_message("⚙️ НАСТРОЙКИ АВТОЗАПУСКА:")
            
            # Проверяем автозапуск DPI
            dpi_autostart = get_dpi_autostart()
            status_dpi = "✅ Включен" if dpi_autostart else "❌ Отключен"
            self.log_message(f"   DPI автозапуск: {status_dpi}")
            
            # Проверяем автозагрузку стратегий
            strategy_autoload = get_strategy_autoload()
            status_strategy = "✅ Включена" if strategy_autoload else "❌ Отключена"
            self.log_message(f"   Автозагрузка стратегий: {status_strategy}")
            
            # Проверяем системный автозапуск
            self._check_system_autostart()
            
        except Exception as e:
            self.log_message(f"❌ Ошибка проверки настроек автозапуска: {e}")

    def _check_system_autostart(self):
        """Проверяет наличие системного автозапуска"""
        try:
            # Проверяем автозапуск через планировщик задач
            command = [
                "schtasks", "/query", "/tn", "ZapretAutoStart", "/fo", "csv"
            ]

            result = subprocess.run(command, capture_output=True, text=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            # ✅ ИСПРАВЛЕНИЕ: Правильно обрабатываем результат
            if result and result.returncode == 0 and result.stdout:
                if "ZapretAutoStart" in result.stdout:
                    self.log_message("   Системный автозапуск: ✅ Активен (планировщик задач)")
                else:
                    self._check_registry_autostart()
            else:
                self._check_registry_autostart()
                    
        except Exception as e:
            self.log_message(f"   Системный автозапуск: ❌ Ошибка проверки ({e})")
            
    def _check_registry_autostart(self):
        """Проверяет автозапуск через реестр"""
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                try:
                    winreg.QueryValueEx(key, "Zapret")
                    self.log_message("   Системный автозапуск: ✅ Активен (реестр)")
                except FileNotFoundError:
                    self.log_message("   Системный автозапуск: ❌ Не настроен")
                    
        except Exception:
            self.log_message("   Системный автозапуск: ❓ Статус неизвестен")

    def get_strategy_info_summary(self):
        """Возвращает краткую сводку о текущей стратегии для основного лога"""
        try:
            checker = StrategyChecker()
            strategy_info = checker.check_current_strategy()
            
            status_icon = "✅" if strategy_info['file_status'] in ['found', 'N/A'] else "❌"
            
            # Формируем краткую сводку
            summary = f"Стратегия: {strategy_info['name']} ({strategy_info['type']})"
            
            if strategy_info['type'] == 'combined':
                details = strategy_info.get('details', {})
                if details.get('active_categories'):
                    summary += f" [{', '.join(details['active_categories'])}]"
            
            return summary
            
        except Exception as e:
            return f"Ошибка получения информации о стратегии: {e}"

    def check_curl_domain(self, domain):
        """Проверяет доступность домена через curl с проверкой остановки."""
        if self.is_stop_requested():
            return
            
        try:
            self.log_message(f"Curl-тест: {domain}")
            
            if not self.is_curl_available():
                self.log_message("  ⚠️ curl не найден в системе, пропускаем HTTP-тесты")
                return
            
            if self.is_stop_requested():
                return
                
            # 1. Сначала проверяем доступность 443 порта
            self.check_port_443(domain)
            
            if self.is_stop_requested():
                return
            
            # 2. Затем делаем полноценный HTTPS запрос
            curl_exe = self._get_curl_path()
            if not curl_exe:
                self.log_message("  ⚠️ curl не найден")
                return
                
            command = [
                curl_exe,
                "-I",  # Только заголовки
                "--connect-timeout", "3",  # Уменьшаем таймауты
                "--max-time", "8", 
                "--silent",
                "--show-error",
                f"https://{domain}/"
            ]

            result = subprocess.run(command, capture_output=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            if self.is_stop_requested():
                return
            
            # Анализируем результат
            if result and result.returncode == 0:
                output = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
                        
                lines = output.strip().split('\n') if output else []
                status_line = lines[0] if lines else ""
                
                if "HTTP/" in status_line:
                    try:
                        status_code = status_line.split()[1]
                        if status_code.startswith('2'):
                            self.log_message(f"  ✅ HTTPS доступен (HTTP {status_code})")
                        elif status_code.startswith('3'):
                            self.log_message(f"  ↗️ HTTPS перенаправление (HTTP {status_code})")
                        elif status_code.startswith('4'):
                            self.log_message(f"  ⚠️ HTTPS клиентская ошибка (HTTP {status_code})")
                        elif status_code.startswith('5'):
                            self.log_message(f"  ❌ HTTPS серверная ошибка (HTTP {status_code})")
                        else:
                            self.log_message(f"  ❓ HTTPS неизвестный статус (HTTP {status_code})")
                    except IndexError:
                        self.log_message(f"  ✅ HTTPS соединение установлено")
                else:
                    self.log_message(f"  ✅ HTTPS соединение установлено")
                    
            else:
                error_output = result.stderr.decode('utf-8', errors='ignore') if result and result.stderr else ""
                
                if "could not resolve host" in error_output.lower():
                    self.log_message(f"  ❌ DNS не разрешается")
                elif "connection timed out" in error_output.lower():
                    self.log_message(f"  ⏱️ HTTPS таймаут соединения")
                elif "connection refused" in error_output.lower():
                    self.log_message(f"  🚫 HTTPS соединение отклонено")
                elif "ssl" in error_output.lower() or "certificate" in error_output.lower():
                    self.log_message(f"  🔒 Проблема с SSL/сертификатом")
                else:
                    self.log_message(f"  ❌ HTTPS недоступен")
            
        except subprocess.TimeoutExpired:
            if not self.is_stop_requested():
                self.log_message(f"  ⏱️ Таймаут HTTPS curl-запроса")
        except FileNotFoundError:
            if not self.is_stop_requested():
                self.log_message(f"  ⚠️ curl не найден в PATH")
        except Exception as e:
            if not self.is_stop_requested():
                self.log_message(f"  ❌ Ошибка HTTPS curl-теста: {str(e)}")

    def _get_curl_path(self):
        """Находит путь к curl"""
        curl_paths = [
            "C:\\Windows\\System32\\curl.exe",
            "C:\\Windows\\SysWOW64\\curl.exe",
            "curl.exe",
            "curl"
        ]
        
        for path in curl_paths:
            try:
                test_result = subprocess.run(
                    [path, "--version"], 
                    capture_output=True, 
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if test_result.returncode == 0:
                    return path
            except:
                continue
        
        return None

    def check_port_443(self, domain):
        """Проверяет доступность 443 порта через telnet/nc или Python socket."""
        try:
            # Используем Python socket для проверки порта
            import socket
            
            self.log_message(f"  🔍 Проверка порта 443 для {domain}...")
            
            # Создаем сокет и пытаемся подключиться
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 секунд таймаут
            
            try:
                result = sock.connect_ex((domain, 443))
                
                if result == 0:
                    self.log_message(f"  ✅ Порт 443 открыт")
                    
                    # Дополнительно проверяем SSL handshake
                    try:
                        import ssl
                        context = ssl.create_default_context()
                        
                        with socket.create_connection((domain, 443), timeout=5) as sock:
                            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                                cert = ssock.getpeercert()
                                if cert:
                                    subject = dict(x[0] for x in cert['subject'])
                                    common_name = subject.get('commonName', 'Unknown')
                                    self.log_message(f"  🔒 SSL handshake успешен (CN: {common_name})")
                                else:
                                    self.log_message(f"  🔒 SSL handshake успешен")
                                    
                    except Exception as ssl_e:
                        self.log_message(f"  ⚠️ Порт 443 открыт, но SSL handshake неудачен: {str(ssl_e)}")
                        
                else:
                    self.log_message(f"  ❌ Порт 443 закрыт или недоступен (код: {result})")
                    
            finally:
                sock.close()
                
        except socket.timeout:
            self.log_message(f"  ⏱️ Таймаут при проверке порта 443")
        except socket.gaierror as e:
            self.log_message(f"  ❌ DNS ошибка при проверке порта 443: {str(e)}")
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при проверке порта 443: {str(e)}")

    def check_curl_http(self, domain):
        """Проверка HTTP (без HTTPS)."""
        try:
            # Добавляем проверку порта 80
            self.check_port_80(domain)
            
            curl_exe = self._get_curl_path()
            if not curl_exe:
                self.log_message("  ⚠️ curl не найден")
                return
            
            command = [
                curl_exe, "-I",
                "--connect-timeout", "5",
                "--max-time", "10",
                "--silent", "--show-error",
                f"http://{domain}/"
            ]

            result = subprocess.run(command, capture_output=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            if result and result.returncode == 0:
                output = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
                        
                lines = output.strip().split('\n') if output else []
                status_line = lines[0] if lines else ""
                if "HTTP/" in status_line:
                    status_code = status_line.split()[1] if len(status_line.split()) > 1 else "???"
                    self.log_message(f"  ✅ HTTP доступен (код {status_code})")
                else:
                    self.log_message(f"  ✅ HTTP соединение установлено")
            else:
                self.log_message(f"  ❌ HTTP недоступен")
                
        except Exception as e:
            self.log_message(f"  ❌ Ошибка HTTP теста: {str(e)}")

    def check_port_80(self, domain):
        """Проверяет доступность 80 порта."""
        try:
            import socket
            
            self.log_message(f"  🔍 Проверка порта 80 для {domain}...")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # 3 секунды для HTTP
            
            try:
                result = sock.connect_ex((domain, 80))
                
                if result == 0:
                    self.log_message(f"  ✅ Порт 80 открыт")
                else:
                    self.log_message(f"  ❌ Порт 80 закрыт или недоступен")
                    
            finally:
                sock.close()
                
        except Exception as e:
            self.log_message(f"  ❌ Ошибка при проверке порта 80: {str(e)}")

    def check_curl_extended(self):
        """Расширенная проверка через curl с различными параметрами."""
        test_domain = "rr2---sn-axq7sn7z.googlevideo.com"
        
        self.log_message("=" * 40)
        self.log_message("Расширенная curl-диагностика:")
        self.log_message("=" * 40)
        
        # Тест 1: Проверка портов и базовое HTTPS соединение
        self.log_message(f"1. Проверка портов и HTTPS для {test_domain}:")
        self.check_curl_domain(test_domain)
        
        # Тест 2: HTTP (без шифрования)
        self.log_message(f"2. HTTP тест (без шифрования):")
        self.check_curl_http(test_domain)
        
        # Тест 3: С игнорированием SSL ошибок
        self.log_message(f"3. HTTPS с игнорированием SSL:")
        self.check_curl_insecure(test_domain)
        
        # Тест 4: Проверка с различными TLS версиями
        self.log_message(f"4. Тест различных TLS версий:")
        self.check_tls_versions(test_domain)

    def check_tls_versions(self, domain):
        """Проверяет доступность с различными версиями TLS."""
        curl_exe = self._get_curl_path()
        if not curl_exe:
            self.log_message("  ⚠️ curl не найден")
            return
            
        tls_versions = [
            ("TLS 1.2", "--tlsv1.2"),
            ("TLS 1.3", "--tlsv1.3"),
            ("TLS 1.1", "--tlsv1.1"),
            ("TLS 1.0", "--tlsv1.0")
        ]
        
        for version_name, tls_flag in tls_versions:
            try:
                command = [
                    curl_exe, "-I", "-k",  # -k игнорирует SSL ошибки
                    "--connect-timeout", "3",
                    "--max-time", "8",
                    "--silent", "--show-error",
                    tls_flag,
                    f"https://{domain}/"
                ]

                result = subprocess.run(command, capture_output=True, timeout=10,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

                if result and result.returncode == 0:
                    output = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
                            
                    lines = output.strip().split('\n') if output else []
                    status_line = lines[0] if lines else ""
                    if "HTTP/" in status_line:
                        status_code = status_line.split()[1] if len(status_line.split()) > 1 else "???"
                        self.log_message(f"  ✅ {version_name} работает (код {status_code})")
                    else:
                        self.log_message(f"  ✅ {version_name} соединение установлено")
                else:
                    self.log_message(f"  ❌ {version_name} не работает")
                    
            except Exception as e:
                self.log_message(f"  ❌ Ошибка теста {version_name}: {str(e)}")

    def check_curl_insecure(self, domain):
        """Проверка HTTPS с игнорированием SSL ошибок."""
        try:
            curl_exe = self._get_curl_path()
            if not curl_exe:
                self.log_message("  ⚠️ curl не найден")
                return
                
            command = [
                curl_exe, "-I", "-k",  # -k игнорирует SSL ошибки
                "--connect-timeout", "5", 
                "--max-time", "10",
                "--silent", "--show-error",
                f"https://{domain}/"
            ]

            result = subprocess.run(command, capture_output=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            if result and result.returncode == 0:
                output = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
                        
                lines = output.strip().split('\n') if output else []
                status_line = lines[0] if lines else ""
                if "HTTP/" in status_line:
                    status_code = status_line.split()[1] if len(status_line.split()) > 1 else "???"
                    self.log_message(f"  ✅ HTTPS доступен с -k (код {status_code})")
                else:
                    self.log_message(f"  ✅ HTTPS соединение установлено с -k")
            else:
                self.log_message(f"  ❌ HTTPS недоступен даже с -k")
                
        except Exception as e:
            self.log_message(f"  ❌ Ошибка HTTPS -k теста: {str(e)}")

    def is_curl_available(self):
        """Проверяет доступность curl в системе."""
        try:
            if not hasattr(self, '_curl_available'):
                self._curl_available = (self._get_curl_path() is not None)
                
                if self._curl_available:
                    self.log_message(f"Найден curl")
                
            return self._curl_available
            
        except Exception as e:
            if hasattr(self, 'log_message'):
                self.log_message(f"Ошибка проверки curl: {e}")
            self._curl_available = False
            return False
    
    def run(self):
        """Выполнение тестов в отдельном потоке с корректной остановкой."""
        try:
            self.log_message(f"Запуск тестирования соединения ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
            self.log_message("="*50)
            
            if self.test_type == "discord":
                self.check_discord()
            elif self.test_type == "youtube":
                self.check_youtube()
            elif self.test_type == "all":
                self.check_discord()
                if not self.is_stop_requested():
                    self.log_message("\n" + "="*30 + "\n")
                    self.check_youtube()
            
            if self.is_stop_requested():
                self.log_message("⚠️ Тестирование остановлено пользователем")
            else:
                self.log_message("="*50)
                self.log_message("Тестирование завершено")
                
        except Exception as e:
            if not self.is_stop_requested():
                self.log_message(f"❌ Критическая ошибка в тесте: {str(e)}")
        finally:
            # ✅ ВСЕГДА эмитируем сигнал завершения
            self.finished_signal.emit()

class LogSendWorker(QObject):
    """Воркер для отправки лога в Telegram в отдельном потоке"""
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, log_path: str, caption: str):
        super().__init__()
        self.log_path = log_path
        self.caption = caption
    
    def run(self):
        try:
            success, error_msg = send_log_file(self.log_path, self.caption)
            if success:
                self.finished.emit(True, "Лог успешно отправлен!")
            else:
                self.finished.emit(False, error_msg or "Ошибка отправки")
        except Exception as e:
            self.finished.emit(False, str(e))

class ConnectionTestDialog(QDialog):
    """Неблокирующее диалоговое окно для тестирования соединений."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Тестирование соединения")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        # Делаем окно модальным, но НЕ блокирующим основной поток
        self.setModal(False)
        
        # Флаг для предотвращения множественных запусков
        self.is_testing = False
        self.is_sending_log = False  # Новый флаг для отправки лога
        
        self.init_ui()
        self.worker = None
        self.worker_thread = None
        self.log_send_thread = None  # Для отправки лога

    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        layout = QVBoxLayout()
        
        # Заголовок
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import Qt
        
        title_label = QLabel("🔍 Диагностика сетевых соединений")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # Комбобокс для выбора теста
        self.test_combo = QComboBox(self)
        self.test_combo.addItems([
            "🌐 Все тесты (Discord + YouTube)", 
            "🎮 Только Discord", 
            "🎬 Только YouTube"
        ])
        self.test_combo.setStyleSheet("padding: 8px; font-size: 12px;")
        layout.addWidget(self.test_combo)
        
        # Кнопки управления тестами
        button_layout = QVBoxLayout()
        
        # Основные кнопки в горизонтальном layout
        main_buttons_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶️ Начать тестирование", self)
        self.start_button.clicked.connect(self.start_test_async)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        main_buttons_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ Остановить тест", self)
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        main_buttons_layout.addWidget(self.stop_button)
        
        button_layout.addLayout(main_buttons_layout)
        
        # Дополнительные кнопки
        extra_buttons_layout = QHBoxLayout()
        
        self.dns_check_button = QPushButton("🌐 Проверка DNS подмены", self)
        self.dns_check_button.clicked.connect(self.show_dns_check)
        self.dns_check_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        extra_buttons_layout.addWidget(self.dns_check_button)
        
        # ИЗМЕНЕНО: Заменяем кнопку "Сохранить лог" на "Отправить лог"
        self.send_log_button = QPushButton("📤 Отправить лог в поддержку", self)
        self.send_log_button.clicked.connect(self.send_log_to_telegram)
        self.send_log_button.setEnabled(False)
        self.send_log_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        extra_buttons_layout.addWidget(self.send_log_button)
        
        button_layout.addLayout(extra_buttons_layout)
        
        layout.addLayout(button_layout)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("margin: 10px 0;")
        layout.addWidget(separator)
        
        # Прогресс-бар
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 20px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Статус тестирования
        self.status_label = QLabel("Готово к тестированию")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("padding: 5px; font-weight: bold; color: #666;")
        layout.addWidget(self.status_label)
        
        # Текстовое поле для вывода результатов
        self.result_text = QTextEdit(self)
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        # Кнопка закрытия
        close_button = QPushButton("❌ Закрыть", self)
        close_button.clicked.connect(self.close_dialog_safely)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        layout.addWidget(close_button)
        
        self.setLayout(layout)

    def send_log_to_telegram(self):
        """Отправляет лог тестирования в Telegram"""
        if self.is_sending_log:
            QMessageBox.information(self, "Отправка в процессе", 
                                "Лог уже отправляется, подождите...")
            return
        
        # Проверяем наличие лог-файла
        temp_log_path = os.path.join(LOGS_FOLDER, "connection_test_temp.log")
        
        if not os.path.exists(temp_log_path):
            QMessageBox.warning(self, "Ошибка", 
                            "Файл журнала не найден.\n"
                            "Сначала выполните тестирование.")
            return
        
        # ✅ ИСПРАВЛЕНИЕ: Правильно обрабатываем возвращаемое значение
        try:
            # Проверяем настройки бота
            bot_connected = check_bot_connection()
            
            if not bot_connected:
                error_msg = "Не удалось подключиться к Telegram боту"
            else:
                error_msg = None
                
        except Exception as e:
            bot_connected = False
            error_msg = str(e)
        
        if not bot_connected:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Бот не настроен")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText(
                f"Не удалось подключиться к боту для отправки логов.\n\n"
                f"Ошибка: {error_msg or 'Неизвестная ошибка'}\n\n"
                "Хотите сохранить лог локально?"
            )
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if msg_box.exec() == QMessageBox.StandardButton.Yes:
                self.save_log_locally()
            return
        
        # Подготавливаем caption с информацией
        import time
        test_type = self.test_combo.currentText()
        caption = (
            f"📊 <b>Лог тестирования соединений</b>\n"
            f"Тип: {test_type}\n"
            f"Zapret v{APP_VERSION}\n"
            f"ID: <code>{get_client_id()}</code>\n"
            f"Host: {platform.node()}\n"
            f"Time: {time.strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        # Блокируем кнопку
        self.send_log_button.setEnabled(False)
        self.is_sending_log = True
        
        # Обновляем статус
        self.status_label.setText("📤 Отправка лога в Telegram...")
        self.status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        
        # Показываем прогресс
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        
        # Создаем воркер и поток для отправки
        self.log_send_thread = QThread(self)
        self.log_send_worker = LogSendWorker(temp_log_path, caption)
        self.log_send_worker.moveToThread(self.log_send_thread)
        
        # Подключаем сигналы
        self.log_send_thread.started.connect(self.log_send_worker.run)
        self.log_send_worker.finished.connect(self.on_log_sent)
        self.log_send_worker.finished.connect(self.log_send_thread.quit)
        self.log_send_worker.finished.connect(self.log_send_worker.deleteLater)
        self.log_send_thread.finished.connect(self.log_send_thread.deleteLater)
        
        # Запускаем отправку
        self.log_send_thread.start()
        
        from log import log
        log(f"Отправка лога тестирования в Telegram", "INFO")
    
    def on_log_sent(self, success: bool, message: str):
        """Обработчик завершения отправки лога"""
        # Скрываем прогресс
        self.progress_bar.setVisible(False)
        
        # Разблокируем кнопку
        self.send_log_button.setEnabled(True)
        self.is_sending_log = False
        
        if success:
            # Обновляем статус
            self.status_label.setText("✅ Лог успешно отправлен!")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            # Добавляем сообщение в результаты
            self.result_text.append("\n" + "=" * 50)
            self.result_text.append("✅ Лог успешно отправлен в канал поддержки!")
            self.result_text.append("Спасибо за помощь в улучшении программы!")
            
            # Показываем уведомление
            QMessageBox.information(
                self,
                "Успешно",
                "Лог тестирования успешно отправлен!\n\n"
                "Техническая поддержка получит ваш отчет и сможет "
                "проанализировать проблемы с подключением."
            )
            
            # Удаляем временный файл после успешной отправки
            try:
                temp_log_path = os.path.join(LOGS_FOLDER, "connection_test_temp.log")
                if os.path.exists(temp_log_path):
                    os.remove(temp_log_path)
            except:
                pass
                
        else:
            # Обновляем статус об ошибке
            self.status_label.setText("❌ Ошибка отправки лога")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            
            # Предлагаем сохранить локально
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Ошибка отправки")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText(
                f"Не удалось отправить лог:\n{message}\n\n"
                "Хотите сохранить лог локально?"
            )
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if msg_box.exec() == QMessageBox.StandardButton.Yes:
                self.save_log_locally()
        
        # Очищаем ссылки
        self.log_send_worker = None
        self.log_send_thread = None
    
    def save_log_locally(self):
        """Сохраняет лог локально как запасной вариант"""
        temp_log_path = os.path.join(LOGS_FOLDER, "connection_test_temp.log")
        
        if not os.path.exists(temp_log_path):
            QMessageBox.warning(self, "Ошибка", "Файл журнала не найден.")
            return
        
        try:
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(
                LOGS_FOLDER, 
                f"connection_test_{timestamp}.log"
            )
            
            # Копируем файл
            with open(temp_log_path, "r", encoding="utf-8-sig") as src, \
                 open(save_path, "w", encoding="utf-8-sig") as dest:
                dest.write(src.read())
            
            QMessageBox.information(
                self, 
                "💾 Сохранено локально", 
                f"Лог сохранен в файл:\n{save_path}\n\n"
                "Вы можете отправить этот файл в техподдержку вручную."
            )
            
            # Открываем папку с файлом
            import subprocess
            subprocess.run(f'explorer /select,"{save_path}"', shell=True)
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Ошибка при сохранении", 
                f"Не удалось сохранить файл журнала:\n{str(e)}"
            )
    
    def show_dns_check(self):
        """Показывает диалог проверки DNS"""
        try:
            # Логируем действие
            from log import log
            log("Открытие диалога проверки DNS из теста соединений", "INFO")
            
            # Если идет тестирование, предупреждаем
            if self.is_testing:
                reply = QMessageBox.question(
                    self,
                    "Тест выполняется",
                    "Сетевой тест еще выполняется.\nОткрыть проверку DNS в отдельном окне?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Создаем и показываем диалог DNS проверки
            dns_dialog = DNSCheckDialog(self)
            dns_dialog.exec()
            
        except Exception as e:
            from log import log
            log(f"Ошибка открытия DNS диалога: {e}", "❌ ERROR")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть проверку DNS:\n{str(e)}"
            )
    
    def start_test_async(self):
        """✅ Асинхронно запускает выбранный тест."""
        if self.is_testing:
            QMessageBox.information(self, "Тест уже выполняется", 
                                "Дождитесь завершения текущего теста")
            return
        
        # Определяем тип теста
        selection = self.test_combo.currentText()
        test_type = "all"
        
        if "Только Discord" in selection:
            test_type = "discord"
        elif "Только YouTube" in selection:
            test_type = "youtube"
        
        # Подготавливаем UI
        self.result_text.clear()
        self.result_text.append(f"🚀 Запуск тестирования: {selection}")
        self.result_text.append("=" * 50)
        
        # Обновляем состояние кнопок
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.dns_check_button.setEnabled(False)  # Блокируем DNS проверку во время теста
        self.test_combo.setEnabled(False)

        # Показываем прогресс
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("🔄 Тестирование в процессе...")
        self.status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        
        # ✅ СОЗДАЕМ ОТДЕЛЬНЫЙ ПОТОК ДЛЯ WORKER'а
        self.worker_thread = QThread(self)           # привязываем к диалогу
        self.worker = ConnectionTestWorker(test_type)
        
        # ✅ ПЕРЕНОСИМ WORKER В ОТДЕЛЬНЫЙ ПОТОК
        self.worker.moveToThread(self.worker_thread)
        
        # ✅ ПОДКЛЮЧАЕМ СИГНАЛЫ
        self.worker_thread.started.connect(self.worker.run)
        self.worker.update_signal.connect(self.update_result_async)
        self.worker.finished_signal.connect(self.on_test_finished_async)
        
        # корректная очистка
        self.worker.finished_signal.connect(self.worker_thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        # Устанавливаем флаг
        self.is_testing = True
        
        # запускаем
        self.worker_thread.start()
        
        from log import log
        log(f"Запуск асинхронного теста соединения: {test_type}", "INFO")
    
    def stop_test(self):
        """✅ Корректно останавливает текущий тест БЕЗ БЛОКИРОВКИ GUI."""
        if not self.worker or not self.worker_thread:
            return
            
        # Показываем статус остановки
        self.result_text.append("\n⚠️ Остановка теста...")
        self.status_label.setText("⏹️ Остановка в процессе...")
        self.status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        
        # Просим worker остановиться
        self.worker.stop_gracefully()
        
        # Создаем таймер для проверки состояния БЕЗ БЛОКИРОВКИ
        from PyQt6.QtCore import QTimer
        
        self.stop_check_timer = QTimer()
        self.stop_check_attempts = 0
        
        def check_thread_stopped():
            self.stop_check_attempts += 1
            
            # ✅ ДОБАВЛЯЕМ ПРОВЕРКУ НА None
            if not self.worker_thread:
                # Поток уже очищен
                self.stop_check_timer.stop()
                self.result_text.append("✅ Тест уже остановлен")
                return
            
            if not self.worker_thread.isRunning():
                # Поток остановился
                self.stop_check_timer.stop()
                self.result_text.append("✅ Тест остановлен корректно")
                self.on_test_finished_async()
                
            elif self.stop_check_attempts > 50:  # 5 секунд (50 * 100мс)
                # Принудительная остановка
                self.stop_check_timer.stop()
                self.result_text.append("⚠️ Принудительная остановка теста...")
                if self.worker_thread:  # ✅ Дополнительная проверка
                    self.worker_thread.terminate()
                    
                    # Даем еще немного времени на terminate
                    QTimer.singleShot(1000, lambda: self._finalize_stop())
                else:
                    self._finalize_stop()
        
        self.stop_check_timer.timeout.connect(check_thread_stopped)
        self.stop_check_timer.start(100)  # Проверяем каждые 100мс

    def _finalize_stop(self):
        """Финализация остановки после terminate."""
        if self.worker_thread and self.worker_thread.isRunning():
            self.result_text.append("❌ Не удалось остановить тест")
        else:
            self.result_text.append("✅ Тест остановлен")
        
        self.on_test_finished_async()
    
    def update_result_async(self, message):
        """✅ Асинхронно обновляет текстовое поле с результатами."""
        # Специальная обработка для DNS сообщений
        if "DNS" in message and "подмен" in message:
            # Добавляем кнопку для быстрого запуска DNS проверки
            self.result_text.append(message)
            self.result_text.append("💡 Совет: Используйте кнопку '🌐 Проверка DNS подмены' для детального анализа")
        else:
            # ✅ THREAD-SAFE обновление GUI
            self.result_text.append(message)
        
        # Автопрокрутка до конца
        scrollbar = self.result_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Обновляем статус с последним сообщением
        if len(message) < 60:
            clean_message = message.replace("✅", "").replace("❌", "").replace("⚠️", "").strip()
            if clean_message:
                self.status_label.setText(f"🔄 {clean_message}")
    
    def on_test_finished_async(self):
        """✅ Асинхронно обрабатывает завершение тестов."""
        # Возвращаем состояние кнопок
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.dns_check_button.setEnabled(True)  # Разблокируем DNS проверку
        self.test_combo.setEnabled(True)
        self.send_log_button.setEnabled(True)
        
        # Скрываем прогресс
        self.progress_bar.setVisible(False)
        
        # Обновляем статус
        self.status_label.setText("✅ Тестирование завершено")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        # Добавляем финальное сообщение
        self.result_text.append("\n" + "=" * 50)
        self.result_text.append("🎉 Тестирование завершено! Лог готов для сохранения.")
        self.result_text.append("💡 Для детальной проверки DNS используйте кнопку '🌐 Проверка DNS подмены'")
        
        # Сбрасываем флаг
        self.is_testing = False
        
        # Очищаем ссылки на поток
        self.worker = None
        self.worker_thread = None
        
        from log import log
        log("Асинхронный тест соединения завершен", "INFO")
    
    def close_dialog_safely(self):
        """Безопасно закрывает диалог."""
        if self.is_testing:
            reply = QMessageBox.question(
                self, 
                "Тест выполняется",
                "Тест еще выполняется. Остановить и закрыть окно?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_test()
                self.close()
        else:
            self.close()
    
    def closeEvent(self, event):
        """Переопределяем событие закрытия окна с улучшенной обработкой."""
        # ✅ Останавливаем таймер если он существует
        if hasattr(self, 'stop_check_timer') and self.stop_check_timer:
            self.stop_check_timer.stop()
            self.stop_check_timer.deleteLater()
        
        if self.is_testing:
            reply = QMessageBox.question(
                self, 
                "Тест выполняется",
                "Тест еще выполняется. Остановить и закрыть окно?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Мягко останавливаем тест
                if self.worker:
                    self.worker.stop_gracefully()
                
                # Ждем завершения
                if self.worker_thread and self.worker_thread.isRunning():
                    if not self.worker_thread.wait(3000):
                        self.worker_thread.terminate()
                        self.worker_thread.wait(1000)
                
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()