import subprocess

class CurlChecker:
    def __init__(self):
        pass
    
    def log_message(self, msg):
        print(f"[LOG] {msg}")
    
    def is_curl_available(self):
        """Проверяет доступность curl в системе."""
        try:
            if not hasattr(self, '_curl_available'):
                if not hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    subprocess.CREATE_NO_WINDOW = 0x08000000
                    
                command = ["curl", "--version"]
                # Временно используем subprocess.run напрямую
                result = run_hidden(
                    command, 
                    timeout=5, 
                    capture_output=True,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                )
                self._curl_available = result.returncode == 0
                
                if self._curl_available:
                    version_info = result.stdout.decode('utf-8', errors='ignore').split('\n')[0]
                    self.log_message(f"Найден curl: {version_info}")
                else:
                    self.log_message(f"curl не найден, returncode: {result.returncode}")
                    if result.stderr:
                        self.log_message(f"stderr: {result.stderr.decode('utf-8', errors='ignore')}")
                
            return self._curl_available
            
        except FileNotFoundError:
            self.log_message("curl не найден в PATH")
            self._curl_available = False
            return False
        except Exception as e:
            self.log_message(f"Ошибка: {type(e).__name__}: {e}")
            self._curl_available = False
            return False

# Тестирование
checker = CurlChecker()
print(f"Curl доступен: {checker.is_curl_available()}")

# Дополнительная проверка
print("\nПрямая проверка curl:")
try:
    result = run_hidden(["curl", "--version"], capture_output=True, text=True)
    print(f"Return code: {result.returncode}")
    print(f"Output: {result.stdout[:100]}...")
except Exception as e:
    print(f"Ошибка: {e}")