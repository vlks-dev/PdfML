"""
Модуль для извлечения именованных сущностей из текста PDF
"""

import spacy
from spacy.glossary import explain
from spacy.tokens import Doc
from spacy.language import Language
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import re
from typing import List, Dict, Any, Optional, Union, cast

from ..utils.logger import get_logger

logger = get_logger(__name__)


class EntityExtractor:
    """
    Класс для извлечения именованных сущностей (имена, даты, организации и т.д.)
    из текста PDF-документов.
    """
    
    def __init__(self, model_type="spacy", model_name="ru_core_news_lg"):
        """
        Инициализация экстрактора сущностей.
        
        Args:
            model_type (str): Тип модели для распознавания сущностей.
                Поддерживаемые значения: "spacy", "transformers"
            model_name (str): Имя модели для загрузки
        """
        self.model_type = model_type
        self.model_name = model_name
        self.model = self._load_model(model_type, model_name)
        
    def _load_model(self, model_type, model_name):
        """
        Загрузка модели для распознавания сущностей.
        
        Args:
            model_type (str): Тип модели
            model_name (str): Имя модели
            
        Returns:
            Загруженную модель
        """
        try:
            if model_type == "spacy":
                model = spacy.load(model_name)
                
                logger.info(f"Загружена модель SpaCy: {model_name}")    
                return model
            elif model_type == "transformers":
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForTokenClassification.from_pretrained(model_name)
                nlp = pipeline("ner", model=model, tokenizer=tokenizer)
                logger.info(f"Загружена модель Transformers: {model_name}")
                return nlp
            else:
                raise ValueError(f"Неподдерживаемый тип модели: {model_type}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise
    
    def extract_entities(self, text):
        """
        Извлечение именованных сущностей из текста.
        
        Args:
            text (str): Текст для анализа
            
        Returns:
            list: Список извлеченных сущностей
        """
        if not text or len(text.strip()) == 0:
            return []
            
        try:
            if self.model_type == "spacy":
                return self._extract_with_spacy(text)
            elif self.model_type == "transformers":
                return self._extract_with_transformers(text)
            else:
                logger.error(f"Неподдерживаемый тип модели: {self.model_type}")
                return []
        except Exception as e:
            logger.error(f"Ошибка при извлечении сущностей: {e}")
            return []
    
    def _extract_with_spacy(self, text: str) -> List[Dict[str, Any]]:
        """
        Извлечение сущностей с использованием SpaCy.
        
        Args:
            text (str): Текст для анализа
            
        Returns:
            list: Список сущностей
        """
        doc = cast(Doc, self.model(text))
        entities = []
        
        for ent in doc.ents:
            # Создаём словарь с информацией о сущности
            entity = {
                "text": ent.text,
                "label": ent.label_,
                "start_char": ent.start_char,
                "end_char": ent.end_char,
                "description": spacy.glossary.explain(ent.label_)
            }
            
            entities.append(entity)
            
        return entities
    
    def _extract_with_transformers(self, text):
        """
        Извлечение сущностей с использованием моделей Transformers.
        
        Args:
            text (str): Текст для анализа
            
        Returns:
            list: Список сущностей
        """
        # Transformers может иметь ограничение на длину текста,
        # поэтому разбиваем на части, если текст длинный
        max_length = 512
        
        if len(text) <= max_length:
            result = self.model(text)
            return self._format_transformer_results(result, text)
        else:
            # Разбиваем текст на части по предложениям
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            entities = []
            offset = 0
            
            for sentence in sentences:
                if len(sentence) == 0:
                    continue
                    
                result = self.model(sentence)
                
                # Корректируем смещение
                formatted_entities = self._format_transformer_results(result, sentence, offset)
                entities.extend(formatted_entities)
                
                # Обновляем смещение для следующего предложения
                offset += len(sentence) + 1  # +1 для пробела между предложениями
                
            return entities
    
    def _format_transformer_results(self, results, text, offset=0):
        """
        Форматирование результатов от модели Transformers.
        
        Args:
            results (list): Результаты от модели
            text (str): Исходный текст
            offset (int): Смещение для позиций символов
            
        Returns:
            list: Отформатированный список сущностей
        """
        entities = []
        
        for entity in results:
            formatted_entity = {
                "text": text[entity["start"]:entity["end"]],
                "label": entity["entity"],
                "start_char": entity["start"] + offset,
                "end_char": entity["end"] + offset,
                "score": entity["score"]
            }
            entities.append(formatted_entity)
            
        return entities
    
    def get_entities_by_type(self, entities, entity_type):
        """
        Фильтрация сущностей по типу.
        
        Args:
            entities (list): Список сущностей
            entity_type (str): Тип сущности для фильтрации
            
        Returns:
            list: Отфильтрованный список сущностей
        """
        return [entity for entity in entities if entity["label"] == entity_type]
        
    def extract_entities_from_pdf_text(self, pdf_text_dict):
        """
        Извлечение сущностей из текста PDF по страницам.
        
        Args:
            pdf_text_dict (dict): Словарь {номер_страницы: текст}
            
        Returns:
            dict: Словарь {номер_страницы: список_сущностей}
        """
        result = {}
        
        for page_num, text in pdf_text_dict.items():
            entities = self.extract_entities(text)
            result[page_num] = entities
            
        return result 