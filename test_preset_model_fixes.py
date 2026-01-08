"""
Тест проверки исправлений в preset_model.py:
1. Формат --out-range=-n8 (вместо --out-range=8n)
2. Порядок аргументов: out-range → send → syndata → strategy
"""

import sys
sys.path.insert(0, r"H:\Privacy\zapretgui")

from preset_zapret2.preset_model import CategoryConfig, SyndataSettings

def test_out_range_format():
    """Проверяем формат --out-range=-n8"""
    print("\n=== Тест 1: Формат --out-range ===")

    # Создаём категорию с syndata настройками
    syndata = SyndataSettings(
        enabled=True,
        out_range=8,
        out_range_mode="n"
    )

    cat = CategoryConfig(
        name="test",
        tcp_args="--lua-desync=fake",
        syndata=syndata
    )

    out_range_arg = cat._get_out_range_args()
    print(f"Сгенерированный аргумент: {out_range_arg}")

    expected = "--out-range=-n8"
    if out_range_arg == expected:
        print(f"✅ PASS: формат правильный '{expected}'")
        return True
    else:
        print(f"❌ FAIL: ожидалось '{expected}', получено '{out_range_arg}'")
        return False

def test_args_order():
    """Проверяем порядок аргументов: out-range → send → syndata → strategy"""
    print("\n=== Тест 2: Порядок аргументов ===")

    syndata = SyndataSettings(
        enabled=True,
        blob="tls_google",
        out_range=8,
        out_range_mode="n",
        send_enabled=True,
        send_repeats=2
    )

    cat = CategoryConfig(
        name="test",
        tcp_args="--lua-desync=fake",
        syndata=syndata
    )

    full_args = cat.get_full_tcp_args()
    print(f"Полные аргументы:\n{full_args}")

    # Разбиваем на части
    parts = full_args.split()
    print(f"\nПорядок аргументов:")
    for i, part in enumerate(parts, 1):
        print(f"  {i}. {part}")

    # Проверяем порядок
    expected_order = [
        "--out-range=-n8",
        "--send=repeats:2",
        "--syndata=blob:tls_google",
        "--lua-desync=fake"
    ]

    success = True
    for i, expected in enumerate(expected_order):
        if i >= len(parts):
            print(f"❌ FAIL: не хватает аргумента '{expected}'")
            success = False
            continue

        actual = parts[i]
        if expected in actual:  # Частичное совпадение (т.к. syndata может быть длиннее)
            print(f"  ✅ Позиция {i+1} правильная: {actual}")
        else:
            print(f"  ❌ Позиция {i+1} неправильная: ожидалось '{expected}', получено '{actual}'")
            success = False

    return success

def test_udp_args_order():
    """Проверяем порядок UDP аргументов"""
    print("\n=== Тест 3: Порядок UDP аргументов ===")

    syndata = SyndataSettings(
        enabled=True,
        blob="quic1",
        out_range=5,
        out_range_mode="d",
        send_enabled=True,
        send_repeats=3
    )

    cat = CategoryConfig(
        name="test",
        udp_args="--lua-desync=tamper:sld",
        syndata=syndata
    )

    full_args = cat.get_full_udp_args()
    print(f"Полные UDP аргументы:\n{full_args}")

    parts = full_args.split()
    print(f"\nПорядок аргументов:")
    for i, part in enumerate(parts, 1):
        print(f"  {i}. {part}")

    # Проверяем, что out-range на первом месте
    if parts[0].startswith("--out-range=-d"):
        print(f"  ✅ Out-range на первом месте")
    else:
        print(f"  ❌ Out-range НЕ на первом месте")
        return False

    # Проверяем, что strategy на последнем месте
    if "--lua-desync=" in parts[-1]:
        print(f"  ✅ Strategy на последнем месте")
    else:
        print(f"  ❌ Strategy НЕ на последнем месте")
        return False

    return True

if __name__ == "__main__":
    print("Запуск тестов для проверки исправлений в preset_model.py")
    print("=" * 60)

    results = []
    results.append(("Out-range формат", test_out_range_format()))
    results.append(("TCP аргументы порядок", test_args_order()))
    results.append(("UDP аргументы порядок", test_udp_args_order()))

    print("\n" + "=" * 60)
    print("ИТОГИ:")
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 Все тесты прошли успешно!")
    else:
        print("\n⚠️ Некоторые тесты провалились!")
        sys.exit(1)
