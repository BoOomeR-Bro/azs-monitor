import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_URL = "https://azs.geoportal40.ru/api/v1/tables/geoportal40/maps/azs/tables/186/geojson?srid=4326&fields=id&fields=ai92&fields=ai95&fields=dt&fields=ai98&fields=ai100&fields=ai95_1&fields=dt_1&fields=name2&fields=name3&fields=address&fields=update"
STATE_FILE = "notified.txt"

def load_notified():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_notified(notified_set):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        for item in notified_set:
            f.write(f"{item}\n")

def main():
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Ошибка получения данных: {e}")
        return

    notified = load_notified()
    new_notifications = []

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        name3 = props.get("name3", "Неизвестная АЗС")
        address = props.get("address", "Адрес не указан")
        update_time = props.get("update", "Неизвестно")
        ai92 = props.get("ai92", False)
        ai95 = props.get("ai95", False)
        station_id = props.get("id")

        # Проверяем наличие АИ-92 ИЛИ АИ-95
        has_fuel = ai92 is True or ai95 is True
        
        if has_fuel:
            if station_id not in notified:
                notified.add(station_id)
                
                # Формируем список доступного топлива для красивого вывода
                fuels = []
                if ai92: fuels.append("АИ-92")
                if ai95: fuels.append("АИ-95")
                fuels_str = " и ".join(fuels)
                
                msg = (
                    f"⛽️ *ЕСТЬ ТОПЛИВО!*\n\n"
                    f"🏢 *{name3}*\n"
                    f"📍 {address}\n"
                    f"✅ В наличии: *{fuels_str}*\n"
                    f"🕒 Обновлено: {update_time}\n\n"
                    f"🔗 [Открыть карту](https://azs.geoportal40.ru/)"
                )
                new_notifications.append(msg)
        
        # Если топлива (и 92, и 95) больше нет, удаляем из списка "уведомленных",
        # чтобы при следующем завозе бензина снова прислать алерт
        elif not has_fuel and station_id in notified:
            notified.remove(station_id)

    if new_notifications:
        save_notified(notified)
        for msg in new_notifications:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown"
            })
        print(f"✅ Отправлено {len(new_notifications)} уведомлений.")
    else:
        print("ℹ️ Изменений в наличии АИ-92 / АИ-95 не обнаружено.")
        save_notified(notified)

if __name__ == "__main__":
    main()
