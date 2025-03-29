"""
Модуль для извлечения данных из форм
"""

import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import numpy as np
from PIL import Image
import fitz
from collections import defaultdict

from ..utils.logger import get_logger

logger = get_logger(__name__)


class FormExtractor:
    """
    Класс для извлечения данных из форм с использованием LayoutLM.
    """
    
    def __init__(self, model_name="microsoft/layoutlmv3-base"):
        """
        Инициализация экстрактора форм.
        
        Args:
            model_name (str): Имя предобученной модели LayoutLM
        """
        self.model_name = model_name
        
        # Загружаем модель и процессор
        try:
            self.processor = LayoutLMv3Processor.from_pretrained(model_name)
            self.model = LayoutLMv3ForTokenClassification.from_pretrained(model_name)
            logger.info(f"Модель {model_name} успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise
        
        # Словарь меток по умолчанию для форм
        self.default_labels = {
            0: "O",        # Outside of any entity
            1: "B-QUESTION",
            2: "I-QUESTION",
            3: "B-ANSWER",
            4: "I-ANSWER",
            5: "B-HEADER",
            6: "I-HEADER",
            7: "B-FIELD",  # Field name
            8: "I-FIELD",
            9: "B-VALUE",  # Field value
            10: "I-VALUE"
        }
        
        # Пользовательские метки могут быть установлены позже
        self.label_map = self.default_labels
        
    def set_label_map(self, label_map):
        """
        Установка пользовательского отображения меток.
        
        Args:
            label_map (dict): Словарь {id: label_name}
        """
        self.label_map = label_map
        logger.info(f"Установлена пользовательская карта меток: {label_map}")
        
    def extract_form_fields(self, pdf_path, page_numbers=None):
        """
        Извлечение полей формы из PDF.
        
        Args:
            pdf_path (str): Путь к PDF-файлу
            page_numbers (list): Список номеров страниц для обработки.
                               Если None, обрабатываются все страницы.
                               
        Returns:
            dict: Словарь {номер_страницы: список_полей}
        """
        # Открываем PDF
        try:
            doc = fitz.Document(pdf_path) 
            
            if page_numbers is None:
                page_numbers = range(len(doc))
                
            result = {}
            
            for page_num in page_numbers:
                if page_num >= len(doc):
                    logger.warning(f"Страница {page_num} не существует")
                    continue
                    
                page = doc[page_num]
                fields = self._process_page(page)
                result[page_num] = fields
                
            doc.close()
            return result
                
        except Exception as e:
            logger.error(f"Ошибка при обработке PDF: {e}")
            return {}
            
    def _process_page(self, page):
        """
        Обработка одной страницы и извлечение полей формы.
        
        Args:
            page: Страница PDF (объект PyMuPDF)
            
        Returns:
            list: Список извлеченных полей
        """
        # Конвертируем страницу в изображение
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72)) # TODO: Нет такого метода get_pixmap
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Получаем текст страницы для дополнительного контекста
        text = page.get_text()
        
        # Выполняем предсказание с помощью модели
        encoding = self.processor(img, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(**encoding)
            
        # Обрабатываем результаты
        predictions = outputs.logits.argmax(-1).squeeze().tolist()
        
        # Получаем bbox для каждого токена
        bbox = encoding.bbox[0].tolist()
        
        # Получаем токены
        tokens = self.processor.tokenizer.convert_ids_to_tokens(encoding.input_ids[0].tolist()) # TODO: Нет такого атрибута tokenizer
        
        # Группируем результаты в поля формы
        fields = []
        current_entity = None
        current_text = ""
        current_box = None
        
        for i, (token, pred, box) in enumerate(zip(tokens, predictions, bbox)):
            label = self.label_map.get(pred, "O")
            
            # Пропускаем специальные токены
            if token.startswith("[CLS]") or token.startswith("[SEP]") or token.startswith("[PAD]"):
                continue
                
            # Начало нового поля
            if label.startswith("B-"):
                # Сохраняем предыдущее поле, если оно есть
                if current_entity is not None and current_text:
                    fields.append({
                        "type": current_entity,
                        "text": current_text.strip(),
                        "bbox": current_box
                    })
                
                # Начинаем новое поле
                current_entity = label[2:]  # Убираем префикс "B-"
                current_text = token.replace("##", "")
                current_box = box
            
            # Продолжение текущего поля
            elif label.startswith("I-") and current_entity == label[2:]:
                current_text += token.replace("##", "")
                
                # Расширяем bbox
                current_box = [
                    min(current_box[0], box[0]), # TODO: Нет такого атрибута box
                    min(current_box[1], box[1]),
                    max(current_box[2], box[2]),
                    max(current_box[3], box[3])
                ]
            
            # Вне полей
            elif label == "O":
                # Сохраняем предыдущее поле, если оно есть
                if current_entity is not None and current_text:
                    fields.append({
                        "type": current_entity,
                        "text": current_text.strip(),
                        "bbox": current_box
                    })
                current_entity = None
                current_text = ""
                current_box = None
        
        # Добавляем последнее поле, если оно есть
        if current_entity is not None and current_text:
            fields.append({
                "type": current_entity,
                "text": current_text.strip(),
                "bbox": current_box
            })
        
        # Связываем поля и значения
        paired_fields = self._pair_fields_and_values(fields)
        
        return paired_fields
    
    def _pair_fields_and_values(self, fields):
        """
        Связывает поля и их значения на основе типов и расположения.
        
        Args:
            fields (list): Список извлеченных полей
            
        Returns:
            list: Список связанных пар поле-значение
        """
        result = []
        
        # Сначала отделяем поля от значений
        field_elements = [f for f in fields if f["type"] == "FIELD"]
        value_elements = [f for f in fields if f["type"] == "VALUE"]
        
        # Для каждого поля ищем ближайшее значение
        for field in field_elements:
            field_box = field["bbox"]
            
            # Находим значения, которые расположены справа или снизу от поля
            candidates = []
            for value in value_elements:
                value_box = value["bbox"]
                
                # Вычисляем расстояние между полем и значением
                # Приоритет: справа, затем снизу
                is_right = value_box[0] >= field_box[2]  # Значение справа от поля
                is_below = value_box[1] >= field_box[3]  # Значение снизу от поля
                
                if is_right or is_below:
                    # Вычисляем евклидово расстояние между центрами
                    field_center = ((field_box[0] + field_box[2]) / 2, (field_box[1] + field_box[3]) / 2)
                    value_center = ((value_box[0] + value_box[2]) / 2, (value_box[1] + value_box[3]) / 2)
                    
                    distance = np.sqrt((field_center[0] - value_center[0])**2 + 
                                       (field_center[1] - value_center[1])**2)
                    
                    candidates.append((value, distance, is_right))
            
            # Сортируем кандидатов по расстоянию и приоритету (справа > снизу)
            candidates.sort(key=lambda x: (not x[2], x[1]))
            
            if candidates:
                # Берем ближайшее значение
                matched_value = candidates[0][0]
                
                # Добавляем пару поле-значение
                result.append({
                    "field_name": field["text"],
                    "field_value": matched_value["text"],
                    "field_bbox": field["bbox"],
                    "value_bbox": matched_value["bbox"]
                })
            else:
                # Если значение не найдено, добавляем только поле
                result.append({
                    "field_name": field["text"],
                    "field_value": "",
                    "field_bbox": field["bbox"],
                    "value_bbox": None
                })
        
        return result
    
    def extract_key_value_pairs(self, text, form_fields=None):
        """
        Извлечение пар ключ-значение из текста с использованием
        регулярных выражений и результатов распознавания форм.
        
        Args:
            text (str): Текст для анализа
            form_fields (list): Уже распознанные поля формы (опционально)
            
        Returns:
            dict: Словарь {ключ: значение}
        """
        # Базовый словарь из распознанных полей формы
        result = {}
        if form_fields:
            for field in form_fields:
                if field["field_name"] and field["field_value"]:
                    result[field["field_name"]] = field["field_value"]
        
        # Дополнительная эвристика для извлечения пар ключ-значение
        # Ищем шаблоны типа "Ключ: Значение" или "Ключ - Значение"
        import re
        
        patterns = [
            r'([A-Za-zА-Яа-я\s]+):\s*([^:\n]+)',  # Ключ: Значение
            r'([A-Za-zА-Яа-я\s]+)\s+-\s+([^-\n]+)',  # Ключ - Значение
            r'([A-Za-zА-Яа-я\s]+)=\s*([^=\n]+)'  # Ключ = Значение
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                
                if key and value and key not in result:
                    result[key] = value
        
        return result 