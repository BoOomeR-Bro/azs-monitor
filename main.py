import os
import requests
import json
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

API_URL = "https://azs.geoportal40.ru/api/v1/tables/geoportal40/maps/azs/tables/186/geojson?srid=4326&fields=id&fields=ai92&fields=ai95&fields=dt&fields=ai98&fields=ai100&fields=ai95_1&fields=dt_1&fields=name2&fields=name3&fields=address&fields=update"

STATE_FILE = "notified.json"
REMINDER_HOURS = 2  # Интервал напоминаний в часах

def load_notified():
    """Загружает состояние с временными метками"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_notified(notified_dict):
    """Сохраняет состояние с временными метками"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(notified_dict, f, indent=2, ensure_ascii=False)

def is_kaluga(address):
    """Проверяет, находится ли заправка в городе Калуга"""
    addr_lower = address.lower().replace(" ", "")
    return "г.калуга" in addr_lower or "калуга," in addr_lower

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
    now = datetime.now()

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        name3 = props.get("name3", "Неизвестная АЗС")
        address = props.get("address", "Адрес не указан")
        update_time = props.get("update", "Неизвестно")
        ai92 = props.get("ai92", False)
        ai95 = props.get("ai95", False)
        station_id = props.get("id")

        # Фильтр: только заправки в г. Калуга
        if not is_kaluga(address):
            continue

        # Проверяем наличие АИ-92 ИЛИ АИ-95
        has_fuel = ai92 is True or ai95 is True

        if has_fuel:
            # Формируем список доступного топлива
            fuels = []
            if ai92: fuels.append("АИ-92")
            if ai95: fuels.append("АИ-95")
            fuels_str = " и ".join(fuels)

            # Проверяем, нужно ли отправить уведомление
            should_notify = False
            is_new = False
            is_reminder = False

            if station_id not in notified:
                # Новая заправка с бензином
                should_notify = True
                is_new = True
            else:
                # Проверяем, прошло ли 2 часа с последнего уведомления
                last_notified = datetime.fromisoformat(notified[station_id])
                if now - last_notified >= timedelta(hours=REMINDER_HOURS):
                    should_notify = True
                    is_reminder = True

            if should_notify:
                # Обновляем время последнего уведомления
                notified[station_id] = now.isoformat()

                # Формируем сообщение
                if is_new:
                    header = "⛽️ *НОВОЕ ТОПЛИВО В КАЛУГЕ!*"
                else:
                    header = "⛽️ *ТОПЛИВО ВСЁ ЕЩЁ ЕСТЬ!*"

                msg = (
                    f"{header}\n\n"
                    f"🏢 *{name3}*\n"
                    f"📍 {address}\n"
                    f"✅ В наличии: *{fuels_str}*\n"
                    f"🕒 Обновлено: {update_time}\n\n"
                    f"🔗 Открыть карту"
                )
                new_notifications.append(msg)

        # Если топлива больше нет, удаляем из списка
        elif not has_fuel and station_id in notified:
            del notified[station_id]

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
        print("ℹ️ Нет новых уведомлений.")

    save_notified(notified)

if __name__ == "__main__":
    main()
