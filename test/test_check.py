import requests
import time

def test_download_speed():
    """Тестирует скорость скачивания большого файла"""
    print("\n📋 Тест 8: Проверка скорости скачивания")
    
    # URL большого файла для тестирования
    download_url = "https://nozapret.ru/Zapret2Setup.exe"
    
    headers = {
        'User-Agent': 'Zapret-App/1.0',
        'Accept': '*/*'
    }
    
    print(f"📦 Тестируем скачивание: {download_url}")
    
    try:
        start_time = time.time()
        
        # Используем stream=True для больших файлов
        response = requests.get(
            download_url, 
            headers=headers,
            timeout=30,
            stream=True,
            verify=True
        )
        
        if response.status_code != 200:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return
        
        # Получаем размер файла из заголовков
        total_size = int(response.headers.get('content-length', 0))
        print(f"📏 Размер файла: {total_size / (1024*1024):.2f} МБ")
        
        # Скачиваем первые несколько мегабайт для теста скорости
        downloaded = 0
        chunk_size = 8192  # 8KB chunks
        max_download = 5 * 1024 * 1024  # Максимум 5 МБ для теста
        
        print("📊 Начинаем тест скорости...")
        
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                downloaded += len(chunk)
                
                # Показываем прогресс каждые 500 КБ
                if downloaded % (500 * 1024) == 0 or downloaded >= max_download:
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed_mbps = (downloaded / (1024 * 1024)) / elapsed
                        print(f"⬇️ Скачано: {downloaded / (1024*1024):.2f} МБ, "
                              f"Скорость: {speed_mbps:.2f} МБ/с")
                
                # Останавливаемся после 5 МБ
                if downloaded >= max_download:
                    print("🛑 Останавливаем тест на 5 МБ")
                    break
        
        end_time = time.time()
        total_time = end_time - start_time
        
        if total_time > 0:
            average_speed = (downloaded / (1024 * 1024)) / total_time
            print(f"\n✅ Тест завершен!")
            print(f"📊 Итоговая статистика:")
            print(f"   📦 Скачано: {downloaded / (1024*1024):.2f} МБ")
            print(f"   ⏱️ Время: {total_time:.2f} сек")
            print(f"   🚀 Средняя скорость: {average_speed:.2f} МБ/с")
            
            # Оценка качества соединения
            if average_speed > 10:
                print("   🟢 Отличное соединение!")
            elif average_speed > 5:
                print("   🟡 Хорошее соединение")
            elif average_speed > 1:
                print("   🟠 Удовлетворительное соединение")
            else:
                print("   🔴 Медленное соединение - возможны timeout'ы")
        
    except requests.exceptions.ReadTimeout:
        print("❌ ReadTimeout: Слишком медленная загрузка")
    except requests.exceptions.ConnectTimeout:
        print("❌ ConnectTimeout: Не удалось подключиться")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ ConnectionError: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

def test_small_vs_large_requests():
    """Сравнивает время ответа для маленьких и больших запросов"""
    print("\n📋 Тест 9: Сравнение маленьких и больших запросов")
    
    urls = {
        "GitHub JSON (маленький)": "https://raw.githubusercontent.com/youtubediscord/src/refs/heads/main/index.json",
        "GitFlic EXE (большой)": "https://gitflic.ru/project/main1234/main1234/blob/raw?file=Zapret2Setup.exe"
    }
    
    headers = {
        'User-Agent': 'Zapret-App/1.0',
        'Accept': '*/*'
    }
    
    for name, url in urls.items():
        print(f"\n🔍 Тестируем: {name}")
        print(f"🔗 URL: {url}")
        
        try:
            start_time = time.time()
            
            # Для больших файлов - только заголовки
            if "большой" in name:
                response = requests.head(url, headers=headers, timeout=15)
            else:
                response = requests.get(url, headers=headers, timeout=15)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"✅ Ответ получен: {response.status_code}")
            print(f"⏱️ Время ответа: {response_time:.3f} сек")
            
            if hasattr(response, 'headers'):
                content_length = response.headers.get('content-length', 'Неизвестно')
                print(f"📦 Размер: {content_length} байт")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")

def test_different_timeouts():
    """Тестирует разные значения timeout для понимания оптимального"""
    print("\n📋 Тест 10: Оптимизация timeout значений")
    
    url = "https://raw.githubusercontent.com/youtubediscord/src/refs/heads/main/index.json"
    timeouts = [5, 10, 15, 20, 30]
    
    headers = {
        'User-Agent': 'Zapret-App/1.0',
        'Accept': 'application/json'
    }
    
    results = []
    
    for timeout_val in timeouts:
        print(f"\n⏰ Тестируем timeout = {timeout_val} сек")
        
        success_count = 0
        total_time = 0
        attempts = 3
        
        for attempt in range(attempts):
            try:
                start_time = time.time()
                response = requests.get(url, headers=headers, timeout=timeout_val)
                end_time = time.time()
                
                if response.status_code == 200:
                    success_count += 1
                    total_time += (end_time - start_time)
                    print(f"  ✅ Попытка {attempt + 1}: {end_time - start_time:.3f}с")
                else:
                    print(f"  ❌ Попытка {attempt + 1}: HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"  ⏰ Попытка {attempt + 1}: Timeout")
            except Exception as e:
                print(f"  ❌ Попытка {attempt + 1}: {e}")
        
        success_rate = (success_count / attempts) * 100
        avg_time = total_time / success_count if success_count > 0 else 0
        
        results.append({
            'timeout': timeout_val,
            'success_rate': success_rate,
            'avg_time': avg_time
        })
        
        print(f"📊 Результат: {success_rate:.1f}% успех, среднее время: {avg_time:.3f}с")
    
    # Анализ результатов
    print(f"\n📈 АНАЛИЗ TIMEOUT ЗНАЧЕНИЙ:")
    print("=" * 50)
    
    best_timeout = None
    best_score = 0
    
    for result in results:
        # Считаем скор: успешность важнее скорости
        score = result['success_rate'] * 0.7 + (30 - result['avg_time'] * 10) * 0.3
        print(f"Timeout {result['timeout']:2d}с: "
              f"{result['success_rate']:5.1f}% успех, "
              f"{result['avg_time']:6.3f}с среднее, "
              f"скор: {score:.1f}")
        
        if score > best_score:
            best_score = score
            best_timeout = result['timeout']
    
    if best_timeout:
        print(f"\n🏆 Рекомендуемый timeout: {best_timeout} секунд")
    else:
        print(f"\n⚠️ Все timeout значения показали плохие результаты")

def main():
    print("🧪 ЗАПУСК ТЕСТИРОВАНИЯ ПОДКЛЮЧЕНИЯ К GITHUB API")
    print("Симуляция условий работы Zapret приложения")
    print("=" * 70)
    
    try:
        test_download_speed()
        test_small_vs_large_requests()
        test_different_timeouts()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n\n💥 Критическая ошибка при тестировании: {e}")

if __name__ == "__main__":
    main()