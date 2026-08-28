import xml.etree.ElementTree as ET
import json
import html
import uuid
from datetime import datetime, timedelta

def convert_xml_to_json(xml_string):
    # 1. Парсим внешний XML с учётом пространства имён
    ns = {'ns': 'http://esb.axelot.ru'}
    root = ET.fromstring(xml_string)
    
    # Извлекаем данные из корневого уровня
    msgid = root.findtext('ns:Id', namespaces=ns)
    creation_time_str = root.findtext('ns:CreationTime', namespaces=ns)
    
    # 2. Декодируем и парсим внутренний XML из <Body>
    body_elem = root.find('ns:Body', ns)
    if body_elem is None or not body_elem.text:
        raise ValueError("Элемент <Body> пуст или не найден")
        
    classdata_xml = html.unescape(body_elem.text)
    classdata = ET.fromstring(classdata_xml)
    
    ссылка = classdata.findtext('Ссылка', '')
    узел_отправки = classdata.findtext('УзелОтправки', '')  # Можно заменить на КодПолучателя, если нужно
    
    товары = classdata.find('Товары')
    rows = товары.findall('row') if товары is not None else []
    
    # Номер заказа берём из первой строки
    номер_заказа = rows[0].findtext('НомерЗаказа', '') if rows else ''
    
    # 3. Обработка дат
    # В вашем примере shipmentdate = 2026-08-26, а CreationTime = 2026-08-27.
    # Вычитаем 1 день, чтобы точно совпасть с логикой вашего примера.
    dt_creation = datetime.fromisoformat(creation_time_str)
    dt_shipment = dt_creation - timedelta(days=1) 
    
    shipment_date_str = dt_shipment.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    date_str = dt_shipment.strftime('%d.%m.%Y')

    # 4. Формируем cargounits (уникальные ПаллетШК, обязательно в нижнем регистре)
    pallet_set = set()
    for row in rows:
        shk = row.findtext('ПаллетШК', '')
        if shk:
            pallet_set.add(shk.strip().lower())
    cargounits = [{"id": p} for p in sorted(list(pallet_set))]

    # 5. Формируем orderrows
    orderrows = []
    for idx, row in enumerate(rows, 1):
        goodid = row.findtext('Номенклатура', '')
        qty_text = row.findtext('Количество', '0')
        qty = int(float(qty_text))  # Преобразуем на случай дробных значений
        date_party_str = row.findtext('ДатаПартии', '')
        
        # Парсим дату партии
        if date_party_str:
            date_party_str = date_party_str.split('.')[0]  # Убираем миллисекунды, если есть
            date_obj = datetime.fromisoformat(date_party_str)
            prodactiondate = date_obj.isoformat() + 'Z'
            name = date_obj.strftime('%d.%m.%Y')
        else:
            prodactiondate = ""
            name = ""
            
        # Генерируем детерминированный UUID для batch.id на основе номенклатуры и даты
        batch_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{goodid}_{date_party_str}"))

        orderrows.append({
            "insuranceprice": 0,
            "goodid": goodid,
            "quantity": 1,  # По вашему примеру всегда 1 (фактическое кол-во уходит в keepingvariantid)
            "id": str(idx),
            "batch": {
                "prodactiondate": prodactiondate,
                "id": batch_id,
                "name": name
            },
            "keepingvariantid": f"Паллета {qty}"
        })

    # 6. Собираем итоговый JSON
    result = {
        "msgid": msgid,
        "request": {
            "order": {
                "orderrows": orderrows,
                "doctype": 3,
                "deliveryinfo": {
                    "delivery": {
                        "id": "2",
                        "name": "Самовывоз"
                    }
                },
                "cargounits": cargounits,
                "id": ссылка,
                "shipmentdate": shipment_date_str,
                "number": номер_заказа,
                "date": date_str,
                "completeset": False
            },
            "logcentreid": узел_отправки
        },
        "token": "***"  # Замените на ваш реальный токен, если нужно
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


# === Использование ===
if __name__ == "__main__":
    try:
        with open('message.xml', 'r', encoding='utf-8') as f:
            xml_content = f.read()
            
        json_output = convert_xml_to_json(xml_content)
        
        with open('output.json', 'w', encoding='utf-8') as f:
            f.write(json_output)
            
        print("✅ JSON успешно сформирован и сохранён в output.json")
    except Exception as e:
        print(f"❌ Ошибка при конвертации: {e}")
