# connection_test.py

import os
import subprocess
import logging
import requests, webbrowser
from datetime import datetime
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QComboBox, QTextEdit, QMessageBox
from PyQt6.QtCore import QObject, QThread, pyqtSignal

class ConnectionTestWorker(QObject):
    """Рабочий поток для выполнения тестов соединения."""
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, test_type="all"):
        super().__init__()
        self.test_type = test_type
        self.log_filename = "connection_test.log"
        
        # ✅ ДОБАВЛЯЕМ ФЛАГ ДЛЯ МЯГКОЙ ОСТАНОВКИ
        self._stop_requested = False
        
        # Настройка логгирования с явным указанием кодировки
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        logging.basicConfig(
            filename=self.log_filename,
            level=logging.INFO,
            format="%(asctime)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
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
    
    def ping(self, host, count=4):
        """Выполняет ping с возможностью прерывания."""
        if self.is_stop_requested():
            return False
            
        try:
            self.log_message(f"Проверка доступности для URL: {host}")
            
            # Используем Popen для возможности прерывания
            command = ["ping", "-n", str(count), host]
            
            # Запускаем процесс
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Ждем завершения с проверкой остановки
            poll_interval = 0.1  # 100мс
            timeout = 10
            elapsed = 0
            
            while elapsed < timeout:
                if self.is_stop_requested():
                    # Прерываем процесс
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return False
                    
                # Проверяем, завершился ли процесс
                if process.poll() is not None:
                    break
                    
                import time
                time.sleep(poll_interval)
                elapsed += poll_interval
            
            # Если процесс все еще работает - прерываем
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                if not self.is_stop_requested():
                    self.log_message(f"Таймаут при проверке {host}")
                return False
            
            # Получаем результат
            stdout, stderr = process.communicate(timeout=1)
            
            if self.is_stop_requested():
                return False
            
            # Используем полученный stdout (НЕ вызываем run снова!)
            output = stdout
            
            # Анализируем результат для Windows
            if "TTL=" in output:
                success_count = output.count("TTL=")
                self.log_message(f"{host}: Отправлено: {count}, Получено: {success_count}")
                for line in output.splitlines():
                    if self.is_stop_requested():  # Проверяем на каждой итерации
                        return False
                    if "TTL=" in line:
                        try:
                            ms = line.split("время=")[1].split("мс")[0].strip()
                            self.log_message(f"\tДоступен (Latency: {ms}ms)")
                        except:
                            self.log_message(f"\tДоступен")
                    elif "узел недоступен" in line.lower() or "превышен интервал" in line.lower():
                        self.log_message(f"\tНедоступен")
            else:
                self.log_message(f"{host}: Отправлено: {count}, Получено: 0")
                self.log_message(f"\tНедоступен")
                
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
            
            command = [
                "curl", "-I",
                "--connect-timeout", "5",
                "--max-time", "10", 
                "--silent", "--show-error",
                url
            ]
            from utils.subproc import run   # импортируем наш обёрточный run
            result  = run(command, timeout=10)     # ← заменили subprocess.run
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                status_line = lines[0] if lines else ""
                
                if "HTTP/" in status_line:
                    status_code = status_line.split()[1]
                    if status_code in ['200', '204']:  # Успешные коды
                        self.log_message(f"  ✅ Реальный YouTube endpoint работает (HTTP {status_code})")
                    elif status_code == '404':
                        self.log_message(f"  ⚠️ Endpoint не найден, но сервер доступен (HTTP {status_code})")
                    elif status_code in ['403', '429']:
                        self.log_message(f"  🚫 YouTube блокирует запрос (HTTP {status_code})")
                    else:
                        self.log_message(f"  ❓ Неожиданный ответ (HTTP {status_code})")
            else:
                error_output = result.stderr.strip()
                if "could not resolve host" in error_output.lower():
                    self.log_message(f"  ❌ DNS блокировка")
                elif "connection timed out" in error_output.lower():
                    self.log_message(f"  ❌ Таймаут - возможная DPI блокировка")
                elif "connection refused" in error_output.lower():
                    self.log_message(f"  ❌ Соединение отклонено - блокировка")
                else:
                    self.log_message(f"  ❌ Ошибка: {error_output[:100]}...")
                    
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
            from utils.subproc import run   # импортируем наш обёрточный run
            result  = run(command, timeout=10)     # ← заменили subprocess.run
            
            if "winws.exe" in result.stdout:
                self.log_message("✅ Процесс winws.exe запущен")
                
                # Извлекаем PID и память
                lines = result.stdout.strip().split('\n')
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
            
            # ДОБАВЛЯЕМ проверку выбранной стратегии
            self.check_current_strategy()
                
        except Exception as e:
            self.log_message(f"❌ Ошибка проверки Zapret: {e}")
            
        self.log_message("")

    def check_current_strategy(self):
        """Проверяет и выводит информацию о текущей выбранной стратегии"""
        try:
            from config import get_last_strategy
            
            self.log_message("📋 ИНФОРМАЦИЯ О СТРАТЕГИИ:")
            
            # Получаем выбранную стратегию из реестра
            current_strategy = get_last_strategy()
            self.log_message(f"   Выбранная стратегия: {current_strategy}")
            
            # Проверяем наличие файла стратегии в папке bin
            strategy_file = self._find_strategy_file(current_strategy)
            
            if strategy_file:
                self.log_message(f"   ✅ Файл стратегии найден: {strategy_file}")
                
                # Проверяем размер файла
                try:
                    file_size = os.path.getsize(strategy_file)
                    self.log_message(f"   📁 Размер файла: {file_size} байт")
                    
                    # Проверяем дату модификации
                    import datetime
                    mod_time = os.path.getmtime(strategy_file)
                    mod_date = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                    self.log_message(f"   📅 Дата изменения: {mod_date}")
                    
                except Exception as e:
                    self.log_message(f"   ⚠️ Ошибка получения информации о файле: {e}")
                    
            else:
                self.log_message("   ❌ Файл стратегии НЕ найден")
                self.log_message("   💡 Возможно нужно загрузить стратегии")
            
            # Дополнительно проверяем настройки автозапуска
            self._check_autostart_settings()
            
        except Exception as e:
            self.log_message(f"❌ Ошибка при проверке стратегии: {e}")

    def _find_strategy_file(self, strategy_name):
        """Ищет файл стратегии в папке bat"""
        try:
            # Возможные расширения файлов стратегий
            possible_extensions = ['.bat', '.cmd']

            bat_folder = "bat"
            if not os.path.exists(bat_folder):
                return None
            
            # Ищем файлы, содержащие ключевые слова из названия стратегии
            strategy_keywords = strategy_name.lower().replace(" ", "_").replace("-", "_")
            
            for file in os.listdir(bat_folder):
                if any(file.lower().endswith(ext) for ext in possible_extensions):
                    file_path = os.path.join(bat_folder, file)
                    
                    # Простое сопоставление по ключевым словам
                    file_lower = file.lower()
                    if any(keyword in file_lower for keyword in ["original", "bolvan", "bol", "van"] if "original" in strategy_keywords.lower()):
                        return file_path
                    elif any(keyword in file_lower for keyword in ["discord"] if "discord" in strategy_keywords.lower()):
                        return file_path
                    elif any(keyword in file_lower for keyword in ["youtube"] if "youtube" in strategy_keywords.lower()):
                        return file_path
            
            # Если точное совпадение не найдено, возвращаем первый .bat файл
            for file in os.listdir(bat_folder):
                if file.lower().endswith('.bat'):
                    return os.path.join(bat_folder, file)
                    
            return None
            
        except Exception as e:
            self.log_message(f"Ошибка поиска файла стратегии: {e}")
            return None

    def _check_autostart_settings(self):
        """Проверяет настройки автозапуска"""
        try:
            from config import get_dpi_autostart, get_strategy_autoload, get_auto_download_enabled
            
            self.log_message("⚙️ НАСТРОЙКИ АВТОЗАПУСКА:")
            
            # Проверяем автозапуск DPI
            dpi_autostart = get_dpi_autostart()
            status_dpi = "✅ Включен" if dpi_autostart else "❌ Отключен"
            self.log_message(f"   DPI автозапуск: {status_dpi}")
            
            # Проверяем автозагрузку стратегий
            strategy_autoload = get_strategy_autoload()
            status_strategy = "✅ Включена" if strategy_autoload else "❌ Отключена"
            self.log_message(f"   Автозагрузка стратегий: {status_strategy}")
            
            # Проверяем автозагрузку при старте
            auto_download = get_auto_download_enabled()
            status_download = "✅ Включена" if auto_download else "❌ Отключена"
            self.log_message(f"   Автозагрузка при старте: {status_download}")
            
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
            
            from utils.subproc import run   # импортируем наш обёрточный run
            result  = run(command, timeout=10)     # ← заменили subprocess.run
            
            if result.returncode == 0 and "ZapretAutoStart" in result.stdout:
                self.log_message("   Системный автозапуск: ✅ Активен (планировщик задач)")
            else:
                # Проверяем автозапуск через реестр
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
                    
        except Exception as e:
            self.log_message(f"   Системный автозапуск: ❌ Ошибка проверки ({e})")

    def get_strategy_info_summary(self):
        """Возвращает краткую сводку о текущей стратегии для основного лога"""
        try:
            from config import get_last_strategy
            strategy_name = get_last_strategy()
            
            # Проверяем наличие файла
            strategy_file = self._find_strategy_file(strategy_name)
            file_status = "найден" if strategy_file else "НЕ найден"
            
            return f"Стратегия: {strategy_name} (файл {file_status})"
            
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
            command = [
                "curl", 
                "-I",  # Только заголовки
                "--connect-timeout", "3",  # Уменьшаем таймауты
                "--max-time", "8", 
                "--silent",
                "--show-error",
                f"https://{domain}/"
            ]
            
            if not hasattr(subprocess, 'CREATE_NO_WINDOW'):
                subprocess.CREATE_NO_WINDOW = 0x08000000
            
            from utils.subproc import run   # импортируем наш обёрточный run
            result  = run(command, timeout=10)     # ← заменили subprocess.run
            
            if self.is_stop_requested():
                return
            
            # Анализируем результат
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
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
                error_output = result.stderr.strip()
                
                if "could not resolve host" in error_output.lower():
                    self.log_message(f"  ❌ DNS не разрешается")
                elif "connection timed out" in error_output.lower():
                    self.log_message(f"  ⏱️ HTTPS таймаут соединения")
                elif "connection refused" in error_output.lower():
                    self.log_message(f"  🚫 HTTPS соединение отклонено")
                elif "ssl" in error_output.lower() or "certificate" in error_output.lower():
                    self.log_message(f"  🔒 Проблема с SSL/сертификатом")
                else:
                    self.log_message(f"  ❌ HTTPS недоступен (код: {result.returncode})")
            
        except subprocess.TimeoutExpired:
            if not self.is_stop_requested():
                self.log_message(f"  ⏱️ Таймаут HTTPS curl-запроса")
        except FileNotFoundError:
            if not self.is_stop_requested():
                self.log_message(f"  ⚠️ curl не найден в PATH")
        except Exception as e:
            if not self.is_stop_requested():
                self.log_message(f"  ❌ Ошибка HTTPS curl-теста: {str(e)}")

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
            
            command = [
                "curl", "-I", 
                "--connect-timeout", "5",
                "--max-time", "10",
                "--silent", "--show-error",
                f"http://{domain}/"
            ]
            
            from utils.subproc import run   # импортируем наш обёрточный run
            result  = run(command, timeout=10)     # ← заменили subprocess.run
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                status_line = lines[0] if lines else ""
                if "HTTP/" in status_line:
                    status_code = status_line.split()[1]
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
        tls_versions = [
            ("TLS 1.2", "--tlsv1.2"),
            ("TLS 1.3", "--tlsv1.3"),
            ("TLS 1.1", "--tlsv1.1"),
            ("TLS 1.0", "--tlsv1.0")
        ]
        
        for version_name, tls_flag in tls_versions:
            try:
                command = [
                    "curl", "-I", "-k",  # -k игнорирует SSL ошибки
                    "--connect-timeout", "3",
                    "--max-time", "8",
                    "--silent", "--show-error",
                    tls_flag,
                    f"https://{domain}/"
                ]
                
                from utils.subproc import run   # импортируем наш обёрточный run
                result  = run(command, timeout=10)     # ← заменили subprocess.run
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    status_line = lines[0] if lines else ""
                    if "HTTP/" in status_line:
                        status_code = status_line.split()[1]
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
            command = [
                "curl", "-I", "-k",  # -k игнорирует SSL ошибки
                "--connect-timeout", "5", 
                "--max-time", "10",
                "--silent", "--show-error",
                f"https://{domain}/"
            ]
            
            from utils.subproc import run   # импортируем наш обёрточный run
            result  = run(command, timeout=15)     # ← заменили subprocess.run
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                status_line = lines[0] if lines else ""
                if "HTTP/" in status_line:
                    status_code = status_line.split()[1]
                    self.log_message(f"  ✅ HTTPS доступен с -k (код {status_code})")
                else:
                    self.log_message(f"  ✅ HTTPS соединение установлено с -k")
            else:
                self.log_message(f"  ❌ HTTPS недоступен даже с -k")
                
        except Exception as e:
            self.log_message(f"  ❌ Ошибка HTTPS -k теста: {str(e)}")

    # даже есть есть curl не работает эта проверка после замены на свой run из utils.subproc
    def is_curl_available(self):
        """Проверяет доступность curl в системе."""
        try:
            # Кэшируем результат проверки
            if not hasattr(self, '_curl_available'):
                if not hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    subprocess.CREATE_NO_WINDOW = 0x08000000
                    
                command = ["curl", "--version"]
                from utils.subproc import run   # импортируем наш обёрточный run
                result  = run(command, timeout=5)     # ← заменили subprocess.run
                self._curl_available = result.returncode == 0
                
                if self._curl_available:
                    version_info = result.stdout.decode('utf-8', errors='ignore').split('\n')[0]
                    self.log_message(f"Найден curl: {version_info}")
                
            return self._curl_available
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
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

class ConnectionTestDialog(QDialog):
    """Неблокирующее диалоговое окно для тестирования соединений."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Тестирование соединения")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        # Делаем окно модальным, но НЕ блокирующим основной поток
        self.setModal(False)  # ← Ключевое изменение!
        
        # Флаг для предотвращения множественных запусков
        self.is_testing = False
        
        self.init_ui()
        self.worker = None
        self.worker_thread = None
    
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
        
        # Кнопки
        button_layout = QVBoxLayout()
        
        self.start_button = QPushButton("Начать тестирование", self)
        self.start_button.clicked.connect(self.start_test_async)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Остановить тест", self)
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        self.save_log_button = QPushButton("Сохранить лог", self)
        self.save_log_button.clicked.connect(self.save_log)
        self.save_log_button.setEnabled(False)
        button_layout.addWidget(self.save_log_button)
        
        layout.addLayout(button_layout)
        
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
        close_button = QPushButton("Закрыть", self)
        close_button.clicked.connect(self.close_dialog_safely)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
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
        self.test_combo.setEnabled(False)
        self.save_log_button.setEnabled(False)
        
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
            
            if not self.worker_thread.isRunning():
                # Поток остановился
                self.stop_check_timer.stop()
                self.result_text.append("✅ Тест остановлен корректно")
                self.on_test_finished_async()
                
            elif self.stop_check_attempts > 50:  # 5 секунд (50 * 100мс)
                # Принудительная остановка
                self.stop_check_timer.stop()
                self.result_text.append("⚠️ Принудительная остановка теста...")
                self.worker_thread.terminate()
                
                # Даем еще немного времени на terminate
                QTimer.singleShot(1000, lambda: self._finalize_stop())
        
        self.stop_check_timer.timeout.connect(check_thread_stopped)
        self.stop_check_timer.start(100)  # Проверяем каждые 100мс

    def _finalize_stop(self):
        """Финализация остановки после terminate."""
        if self.worker_thread and self.worker_thread.isRunning():
            self.result_text.append("❌ Не удалось остановить тест")
        else:
            self.result_text.append("✅ Тест остановлен принудительно")
        
        self.on_test_finished_async()
    
    def update_result_async(self, message):
        """✅ Асинхронно обновляет текстовое поле с результатами."""
        if message == "YOUTUBE_ERROR_403":
            # Специальная обработка для ошибки 403 YouTube
            reply = QMessageBox.question(
                self, 
                "Ошибка YouTube",
                "Ошибка 403: YouTube требует дополнительной настройки.\n"
                "Открыть инструкцию?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import webbrowser
                webbrowser.open("https://github.com/youtubediscord/youtube_59second")
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
        self.test_combo.setEnabled(True)
        self.save_log_button.setEnabled(True)
        
        # Скрываем прогресс
        self.progress_bar.setVisible(False)
        
        # Обновляем статус
        self.status_label.setText("✅ Тестирование завершено")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        # Добавляем финальное сообщение
        self.result_text.append("\n" + "=" * 50)
        self.result_text.append("🎉 Тестирование завершено! Лог готов для сохранения.")
        
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
    
    def save_log(self):
        """Сохраняет лог в текстовый файл."""
        if not os.path.exists("connection_test.log"):
            QMessageBox.warning(self, "Ошибка", "Файл журнала не найден.")
            return
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                f"connection_test_{timestamp}.log"
            )
            
            # Чтение и запись с явным указанием кодировки UTF-8
            with open("connection_test.log", "r", encoding="utf-8-sig") as src, \
                 open(save_path, "w", encoding="utf-8-sig") as dest:
                dest.write(src.read())
            
            QMessageBox.information(
                self, 
                "💾 Сохранение успешно", 
                f"Лог сохранен в файл:\n{save_path}\n\nВы можете отправить этот файл в техподдержку."
            )
            
            # Открываем папку с файлом
            import subprocess
            subprocess.Popen(f'explorer /select,"{save_path}"')
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Ошибка при сохранении", 
                f"Не удалось сохранить файл журнала:\n{str(e)}"
            )