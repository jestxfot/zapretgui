# В файле hosts.py импортируйте переменную PROXY_DOMAINS и используйте её в методе add_proxy_domains:

import ctypes
from PyQt6.QtWidgets import QMessageBox
from proxy_domains import PROXY_DOMAINS  # Импортируем внешний словарь
from log import log

class HostsManager:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback
    
    def set_status(self, message):
        """Отображает статусное сообщение"""
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)

    def show_popup_message(self, title, message):
        """Показывает всплывающее окно с сообщением"""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.information)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except:
            try:
                ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
            except:
                print(f"{title}: {message}")

    def is_proxy_domains_active(self):
        """Проверяет, есть ли в hosts-файле прокси-домены из нашего списка"""
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        try:
            with open(hosts_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Проверяем наличие хотя бы одного домена из PROXY_DOMAINS в файле hosts
            for domain in PROXY_DOMAINS.keys():
                if domain in content:
                    return True
            return False
        except Exception as e:
            log(f"Ошибка при проверке файла hosts: {str(e)}")
            return False

    def remove_proxy_domains(self):
        """Удаляет прокси-записи из файла hosts"""
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        try:
            # Читаем текущее содержимое файла
            with open(hosts_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Фильтруем строки, удаляя те, которые содержат наши прокси-домены
            filtered_lines = []
            domains_to_remove = set(PROXY_DOMAINS.keys())
            
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    filtered_lines.append(line)
                    continue
                    
                parts = line_stripped.split()
                if len(parts) >= 2 and len(parts[1]) > 0:
                    domain = parts[1]
                    if domain in domains_to_remove:
                        continue  # Пропускаем эту строку
                
                filtered_lines.append(line)
            
            # Записываем обратно в файл
            with open(hosts_path, 'w', encoding='utf-8') as file:
                file.writelines(filtered_lines)
            
            self.set_status(f"Файл hosts обновлен: записи прокси-доменов удалены")
            log("Прокси-домены удалены из файла hosts")
            return True
        except PermissionError:
            self.set_status("Ошибка доступа: требуются права администратора")
            log("Ошибка доступа: требуются права администратора")
            return False
        except Exception as e:
            self.set_status(f"Ошибка при обновлении hosts: {str(e)}")
            log(f"Ошибка при обновлении hosts: {str(e)}")
            return False
        
    def modify_hosts_file(self, domain_ip_dict):
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        try:
            with open(hosts_path, 'r', encoding='utf-8') as file:
                original_lines = file.readlines()
            
            final_lines = []
            for line in original_lines:
                line_stripped = line.strip()                
                if not line_stripped or line_stripped.startswith('#'):
                    final_lines.append(line)
                    continue
                    
                parts = line_stripped.split()
                if len(parts) >= 2:
                    _, domain = parts[0], parts[1]
                    if domain in domain_ip_dict:
                        continue
                    else:
                        final_lines.append(line)
            
            new_records = []
            for domain, ip in domain_ip_dict.items():
                new_records.append(f"{ip} {domain}\n")
            
            new_content = new_records + final_lines
            
            with open(hosts_path, 'w', encoding='utf-8') as file:
                file.writelines(new_content)
            
            self.set_status(f"Файл hosts обновлен: добавлено/обновлено {len(domain_ip_dict)} записей")
            log(f"Прокси-домены добавлены/обновлены в файле hosts: {domain_ip_dict}")
            return True
        except PermissionError:
            self.set_status("Ошибка доступа: требуются права администратора")
            log("Ошибка доступа: требуются права администратора")
            return False
        except Exception as e:
            self.set_status(f"Ошибка при обновлении hosts {str(e)}")
            log(f"Ошибка при обновлении hosts: {str(e)}")
            return False

    def add_proxy_domains(self):
        """Добавляет или обновляет прокси домены в файле hosts, используя внешний словарь PROXY_DOMAINS"""
        return self.modify_hosts_file(PROXY_DOMAINS)