import xml.etree.ElementTree as ET
import json
import html
import uuid
from datetime import datetime, timedelta
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLabel, QFileDialog, QTabWidget, 
                             QLineEdit, QMessageBox, QGroupBox, QFormLayout, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor


class ConverterWorker(QThread):
    """Рабочий поток для конвертации"""
    finished = pyqtSignal(str)  # Сигнал с результатом JSON
    error = pyqtSignal(str)     # Сигнал с ошибкой
    
    def __init__(self, xml_content):
        super().__init__()
        self.xml_content = xml_content
    
    def run(self):
        try:
            result = convert_xml_to_json(self.xml_content)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class XMLConverterApp(QMainWindow):
    """Основное окно приложения конвертера XML в JSON"""
    
    def __init__(self):
        super().__init__()
        self.current_filename = None
        self.output_directory = os.getcwd()
        self.init_ui()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle('Конвертер XML в JSON')
        self.setMinimumSize(900, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_label = QLabel('🔄 Конвертер XML → JSON')
        title_label.setFont(QFont('Arial', 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Вкладки
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Вкладка 1: Открытие файла
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)
        file_layout.setSpacing(10)
        
        # Группа выбора файла
        file_group = QGroupBox('Выберите XML файл для конвертации')
        file_group_layout = QVBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText('Путь к файлу не выбран')
        self.file_path_edit.setReadOnly(True)
        file_group_layout.addWidget(self.file_path_edit)
        
        btn_layout = QHBoxLayout()
        self.browse_btn = QPushButton('📁 Обзор...')
        self.browse_btn.clicked.connect(self.browse_file)
        self.browse_btn.setMinimumHeight(35)
        btn_layout.addWidget(self.browse_btn)
        
        self.convert_file_btn = QPushButton('▶ Конвертировать файл')
        self.convert_file_btn.clicked.connect(self.convert_file)
        self.convert_file_btn.setMinimumHeight(35)
        self.convert_file_btn.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold;')
        self.convert_file_btn.setEnabled(False)
        btn_layout.addWidget(self.convert_file_btn)
        
        file_group_layout.addLayout(btn_layout)
        file_layout.addWidget(file_group)
        
        # Вкладка 2: Вставка текста
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        text_layout.setSpacing(10)
        
        text_group = QGroupBox('Вставьте XML содержимое')
        text_group_layout = QVBoxLayout(text_group)
        
        self.xml_text_edit = QTextEdit()
        self.xml_text_edit.setPlaceholderText('Вставьте ваш XML код сюда...')
        self.xml_text_edit.setFont(QFont('Consolas', 10))
        self.xml_text_edit.setMinimumHeight(300)
        text_group_layout.addWidget(self.xml_text_edit)
        
        self.convert_text_btn = QPushButton('▶ Конвертировать текст')
        self.convert_text_btn.clicked.connect(self.convert_text)
        self.convert_text_btn.setMinimumHeight(35)
        self.convert_text_btn.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold;')
        text_group_layout.addWidget(self.convert_text_btn)
        
        text_layout.addWidget(text_group)
        
        self.tabs.addTab(file_tab, '📄 Из файла')
        self.tabs.addTab(text_tab, '✏️ Вставка текста')
        
        # Группа настроек сохранения
        save_group = QGroupBox('Настройки сохранения')
        save_layout = QFormLayout(save_group)
        
        self.output_dir_edit = QLineEdit(self.output_directory)
        self.output_dir_edit.setReadOnly(True)
        save_layout.addRow('Папка сохранения:', self.output_dir_edit)
        
        self.output_file_edit = QLineEdit()
        self.output_file_edit.setPlaceholderText('Имя файла будет заполнено автоматически')
        self.output_file_edit.setReadOnly(True)
        save_layout.addRow('Имя файла:', self.output_file_edit)
        
        change_dir_btn = QPushButton('Изменить папку сохранения')
        change_dir_btn.clicked.connect(self.change_output_directory)
        save_layout.addRow('', change_dir_btn)
        
        main_layout.addWidget(save_group)
        
        # Прогресс бар и статус
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel('Готов к работе')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('color: gray; font-style: italic;')
        main_layout.addWidget(self.status_label)
        
        # Кнопка открытия выходной папки
        open_folder_btn = QPushButton('📂 Открыть папку с результатами')
        open_folder_btn.clicked.connect(self.open_output_folder)
        main_layout.addWidget(open_folder_btn)
        
        # Рабочий поток
        self.worker = None
        
    def browse_file(self):
        """Открыть диалог выбора файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            'Выберите XML файл', 
            '', 
            'XML файлы (*.xml);;Все файлы (*.*)'
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.current_filename = file_path
            self.convert_file_btn.setEnabled(True)
            self.status_label.setText(f'Файл выбран: {os.path.basename(file_path)}')
            
    def change_output_directory(self):
        """Изменить папку для сохранения результатов"""
        directory = QFileDialog.getExistingDirectory(
            self,
            'Выберите папку для сохранения',
            self.output_directory
        )
        
        if directory:
            self.output_directory = directory
            self.output_dir_edit.setText(directory)
            self.status_label.setText(f'Папка сохранения изменена: {directory}')
            
    def convert_file(self):
        """Конвертировать выбранный файл"""
        if not self.current_filename:
            QMessageBox.warning(self, 'Ошибка', 'Пожалуйста, выберите файл!')
            return
            
        try:
            with open(self.current_filename, 'r', encoding='utf-8') as f:
                xml_content = f.read()
                
            self.process_conversion(xml_content, os.path.basename(self.current_filename))
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка чтения файла:\n{str(e)}')
            self.status_label.setText('❌ Ошибка при чтении файла')
            
    def convert_text(self):
        """Конвертировать текст из поля ввода"""
        xml_content = self.xml_text_edit.toPlainText().strip()
        
        if not xml_content:
            QMessageBox.warning(self, 'Ошибка', 'Пожалуйста, вставьте XML содержимое!')
            return
            
        self.process_conversion(xml_content, 'text_input')
        
    def process_conversion(self, xml_content, source_name):
        """Общая логика конвертации"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Бесконечная анимация
        self.status_label.setText('⏳ Конвертация...')
        self.convert_file_btn.setEnabled(False)
        self.convert_text_btn.setEnabled(False)
        
        self.worker = ConverterWorker(xml_content)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.error.connect(self.on_conversion_error)
        self.worker.start()
        
    def on_conversion_finished(self, json_result):
        """Обработка успешной конвертации"""
        self.progress_bar.setVisible(False)
        self.convert_file_btn.setEnabled(True)
        self.convert_text_btn.setEnabled(True)
        
        # Извлекаем НомерОтгрузки1С для имени файла
        filename = self.extract_shipment_number(json_result)
        
        if filename:
            self.output_file_edit.setText(filename)
            
            # Сохраняем файл
            output_path = os.path.join(self.output_directory, filename)
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(json_result)
                    
                self.status_label.setText(f'✅ Успешно сохранено: {filename}')
                QMessageBox.information(
                    self, 
                    'Успех', 
                    f'Файл успешно конвертирован и сохранён!\n\nПуть: {output_path}\nИмя файла: {filename}'
                )
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка сохранения файла:\n{str(e)}')
                self.status_label.setText('❌ Ошибка при сохранении')
        else:
            self.status_label.setText('⚠️ Не удалось извлечь НомерОтгрузки1С')
            QMessageBox.warning(
                self,
                'Предупреждение',
                'Не удалось извлечь НомерОтгрузки1С из XML.\nПроверьте формат входных данных.'
            )
            
    def on_conversion_error(self, error_message):
        """Обработка ошибки конвертации"""
        self.progress_bar.setVisible(False)
        self.convert_file_btn.setEnabled(True)
        self.convert_text_btn.setEnabled(True)
        self.status_label.setText(f'❌ Ошибка: {error_message}')
        QMessageBox.critical(self, 'Ошибка конвертации', error_message)
        
    def extract_shipment_number(self, json_string):
        """Извлечь НомерОтгрузки1С из JSON для формирования имени файла"""
        try:
            data = json.loads(json_string)
            # Пытаемся найти НомерОтгрузки1С в различных местах
            shipment_number = None
            
            # Проверяем различные возможные расположения
            if 'request' in data and 'order' in data['request']:
                order = data['request']['order']
                shipment_number = order.get('shipmentnumber1c') or order.get('номеротгрузки1с')
                
            if not shipment_number:
                # Если не нашли, используем number или ссылку
                if 'request' in data and 'order' in data['request']:
                    order = data['request']['order']
                    shipment_number = order.get('number') or order.get('id')
                    
            if shipment_number:
                # Очищаем имя файла от недопустимых символов
                safe_filename = "".join(c for c in shipment_number if c.isalnum() or c in (' ', '-', '_', '.'))
                safe_filename = safe_filename.strip()
                if not safe_filename.endswith('.json'):
                    safe_filename += '.json'
                return safe_filename
                
        except Exception:
            pass
            
        return f'output_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
    def open_output_folder(self):
        """Открыть папку с результатами в проводнике"""
        try:
            if sys.platform == 'win32':
                os.startfile(self.output_directory)
            elif sys.platform == 'darwin':
                os.system(f'open "{self.output_directory}"')
            else:
                os.system(f'xdg-open "{self.output_directory}"')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось открыть папку:\n{str(e)}')


def convert_xml_to_json(xml_string):
    """Конвертирует XML строку в JSON"""
    # 1. Парсим внешний XML с учётом пространства имён
    ns = {'ns': 'http://esb.axelot.ru'}
    root = ET.fromstring(xml_string)
    
    # Извлекаем данные из корневого уровня
    msgid = root.findtext('ns:Id', namespaces=ns)
    creation_time_str = root.findtext('ns:CreationTime', namespaces=ns)
    
    # Дополнительно извлекаем НомерОтгрузки1С
    shipment_number_1c = root.findtext('ns:НомерОтгрузки1С', namespaces=ns)
    
    # 2. Декодируем и парсим внутренний XML из <Body>
    body_elem = root.find('ns:Body', ns)
    if body_elem is None or not body_elem.text:
        raise ValueError("Элемент <Body> пуст или не найден")
        
    classdata_xml = html.unescape(body_elem.text)
    classdata = ET.fromstring(classdata_xml)
    
    ссылка = classdata.findtext('Ссылка', '')
    узел_отправки = classdata.findtext('УзелОтправки', '')
    
    товары = classdata.find('Товары')
    rows = товары.findall('row') if товары is not None else []
    
    # Номер заказа берём из первой строки
    номер_заказа = rows[0].findtext('НомерЗаказа', '') if rows else ''
    
    # 3. Обработка дат
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
        qty = int(float(qty_text))
        date_party_str = row.findtext('ДатаПартии', '')
        
        # Проверяем атрибут xsi:nil для ПартияКИС
        party_elem = row.find('ПартияКИС')
        is_nil = False
        if party_elem is not None:
            nil_attr = party_elem.get('{http://www.w3.org/2001/XMLSchema-instance}nil')
            if nil_attr == 'true':
                is_nil = True
        
        # Парсим дату партии
        if date_party_str and not is_nil:
            date_party_str = date_party_str.split('.')[0]
            date_obj = datetime.fromisoformat(date_party_str)
            prodactiondate = date_obj.isoformat() + 'Z'
            name = date_obj.strftime('%d.%m.%Y')
        else:
            prodactiondate = ""
            name = ""
            
        # Генерируем детерминированный UUID для batch.id только если не nil
        if is_nil:
            batch_id = ""
        else:
            batch_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{goodid}_{date_party_str}"))

        orderrows.append({
            "insuranceprice": 0,
            "goodid": goodid,
            "quantity": 1,
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
        "token": "***"
    }
    
    # Добавляем НомерОтгрузки1С если он есть
    if shipment_number_1c:
        result["request"]["order"]["shipmentnumber1c"] = shipment_number_1c

    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Устанавливаем стиль приложения
    app.setStyle('Fusion')
    
    window = XMLConverterApp()
    window.show()
    
    sys.exit(app.exec_())
