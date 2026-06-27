# test_xui.py
import uuid
from core.xuiclient import XUIClient  # Импортируем наш класс

# --- НАСТРОЙКИ ДЛЯ ТЕСТА ---
# Вставь сюда реальные данные твоей панели 3x-ui
PANEL_HOST = "https://91.108.240.223:55151/ZsTLghPoaKATGnSlt6/"  # Например: "http://95.213.255.1:2053"
PANEL_TOKEN = "YmWHWzueeKly6crKB8yivumOhtjaC9eCu36SfywafZWSEFRI"
INBOUND_ID = 1  # ID твоего VLESS инбаунда в панели (обычно 1, если он создавался первым)


# ---------------------------

def run_api_tests():
    print("🚀 Начинаем тестирование XUIClient...\n")

    # 1. Инициализация клиента
    client = XUIClient(host=PANEL_HOST, token=PANEL_TOKEN)

    # --- ТЕСТ 1: Проверка связи и авторизации ---
    print("1️⃣ Тест: Получение списка инбаундов (/panel/api/inbounds/list)...")
    inbounds_res = client.get_inbounds()

    if inbounds_res.get("success"):
        print("✅ Успешно! Связь с панелью установлена.")
        inbounds = inbounds_res.get("obj", [])
        if inbounds:
            for inbound in inbounds:
                print(f"   - Найден инбаунд #{inbound['id']}: {inbound['remark']} (Порт: {inbound['port']})")
        else:
            print("   - Инбаунды не найдены (панель пустая).")
    else:
        print(f"❌ Ошибка: {inbounds_res.get('msg')}")
        print("🛑 Прерываем тесты, так как нет связи с панелью.")
        return

    print("-" * 50)

    # --- ТЕСТ 2: Создание клиента ---
    print("2️⃣ Тест: Добавление нового клиента...")
    test_email = f"test_api_{str(uuid.uuid4())[:8]}"  # Генерируем случайное имя
    test_uuid = str(uuid.uuid4())

    print(f"   - Попытка добавить клиента: {test_email} / {test_uuid}")
    add_res = client.add_client(
        inbound_id=INBOUND_ID,
        client_email=test_email,
        client_uuid=test_uuid
    )

    if add_res.get("success"):
        print(f"✅ Успешно! Клиент {test_email} добавлен в инбаунд #{INBOUND_ID}.")
    else:
        print(f"❌ Ошибка добавления: {add_res.get('msg')}")
        # Если не удалось добавить, дальше тестировать нет смысла
        return

    print("-" * 50)

    # --- ТЕСТ 3: Запрос статистики ---
    print("3️⃣ Тест: Получение статистики трафика клиента...")
    traffic_res = client.get_client_traffic(test_email)

    if traffic_res.get("success"):
        obj = traffic_res.get("obj")
        if obj:
            print(f"✅ Успешно! Данные: {obj}")
        else:
            # 3x-ui часто возвращает null/None в 'obj', если клиент еще не потратил ни байта
            print("✅ Запрос прошел успешно (клиент пока не потратил трафик, поэтому obj пустой).")
    else:
        print(f"❌ Ошибка получения статистики: {traffic_res.get('msg')}")

    print("-" * 50)
    print("🎉 Все базовые тесты API завершены!")


if __name__ == "__main__":
    run_api_tests()