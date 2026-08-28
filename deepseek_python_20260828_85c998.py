import xml.etree.ElementTree as ET
import json
import html


def get_text(element, tag, default=''):
    """Безопасное извлечение текста: учитывает nil-элементы и None."""
    el = element.find(tag)
    if el is not None and el.text is not None:
        return el.text.strip()
    return default


def convert_xml_to_json(xml_content):
    # ── 1. Парсим внешний XML ──────────────────────────────
    root = ET.fromstring(xml_content)

    # Пространство имён из корневого элемента
    ns = {'ns': 'http://esb.axelot.ru'}

    body_elem = root.find('ns:Body', ns)
    if body_elem is None:
        body_elem = root.find('Body')          # fallback без ns
    if body_elem is None:
        raise ValueError("Элемент <Body> не найден в XML")

    # ── 2. Декодируем содержимое Body (escaped XML) ───────
    body_raw = body_elem.text or ''
    body_unescaped = html.unescape(body_raw)   # &lt; → <, &gt; → >

    # ── 3. Парсим внутренний XML (classData) ──────────────
    inner_root = ET.fromstring(body_unescaped)

    ссылка          = get_text(inner_root, 'Ссылка')
    код_получателя  = get_text(inner_root, 'КодПолучателя')

    # ── 4. Собираем строки товаров → cargounits ───────────
    товары_elem = inner_root.find('Товары')
    cargounits = []

    if товары_elem is not None:
        for row in товары_elem.findall('row'):
            unit = {
                "weight":         get_text(row, 'Вес'),
                "article":        get_text(row, 'Артикул'),
                "quantity":       get_text(row, 'Количество'),
                "packing":        get_text(row, 'Фасовка'),
                "pallet":         get_text(row, 'Паллет'),
                "palletBarcode":  get_text(row, 'ПаллетШК'),
                "batchDate":      get_text(row, 'ДатаПартии'),
                "orderNumber":    get_text(row, 'НомерЗаказа'),
                "nomenclature":   get_text(row, 'Номенклатура'),
                "shipmentNumber1C": get_text(row, 'НомерОтгрузки1С'),
                "order":          get_text(row, 'Заказ'),
            }
            cargounits.append(unit)

    # ── 5. Служебные поля ─────────────────────────────────
    номер_заказа  = cargounits[0]["orderNumber"] if cargounits else ""
    shipment_date = cargounits[0]["batchDate"]   if cargounits else ""

    creation_time = (
        root.findtext('ns:CreationTime', namespaces=ns)
        or root.findtext('CreationTime')
        or ''
    )
    date_str = creation_time[:10] if creation_time else ""

    # ── 6. Формируем JSON ─────────────────────────────────
    result = {
        "data": {
            "delivery": {
                "type":        {"id": "2", "name": "Самовывоз"},
                "cargounits":  cargounits,
                "id":          ссылка,
                "shipmentdate": shipment_date,
                "number":      номер_заказа,
                "date":        date_str,
                "completeset": False
            },
            "logcentreid": код_получателя
        },
        "token": "***"
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


# === Использование ===
if __name__ == "__main__":
    with open('message.xml', 'r', encoding='utf-8') as f:
        xml_content = f.read()

    json_output = convert_xml_to_json(xml_content)

    with open('output.json', 'w', encoding='utf-8') as f:
        f.write(json_output)

    print("JSON сохранён в output.json")