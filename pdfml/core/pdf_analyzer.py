"""
Основной класс для комплексного анализа PDF-документов
"""

import os
import json
from datetime import datetime

from ..core.pdf_processor import PDFProcessor
from ..extractors.layout_extractor import LayoutExtractor
from ..extractors.table_extractor import TableExtractor
from ..extractors.entity_extractor import EntityExtractor
from ..models.form_extractor import FormExtractor
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PDFAnalyzer:
    """
    Класс для комплексного анализа PDF-документов с использованием
    различных методов извлечения данных.
    """
    
    def __init__(self, pdf_path, use_ocr=False, ocr_lang='rus+eng'):
        """
        Инициализация анализатора PDF.
        
        Args:
            pdf_path (str): Путь к PDF-файлу
            use_ocr (bool): Использовать ли OCR для извлечения текста
            ocr_lang (str): Языки для OCR (формат Tesseract)
        """
        self.pdf_path = pdf_path
        self.use_ocr = use_ocr
        self.ocr_lang = ocr_lang
        
        logger.info(f"Инициализация анализатора для {pdf_path}")
        
        # Инициализируем процессор PDF
        self.pdf_processor = PDFProcessor(pdf_path, use_ocr, ocr_lang)
        
        # Другие экстракторы инициализируются по требованию
        self._layout_extractor = None
        self._table_extractor = None
        self._entity_extractor = None
        self._form_extractor = None
        
        # Результаты анализа
        self.extracted_text = None
        self.layout_results = None
        self.table_results = None
        self.entity_results = None
        self.form_results = None
        
    @property
    def layout_extractor(self):
        """Ленивая инициализация экстрактора макета"""
        if self._layout_extractor is None:
            logger.info("Инициализация экстрактора макета")
            self._layout_extractor = LayoutExtractor()
        return self._layout_extractor
    
    @property
    def table_extractor(self):
        """Ленивая инициализация экстрактора таблиц"""
        if self._table_extractor is None:
            logger.info("Инициализация экстрактора таблиц")
            self._table_extractor = TableExtractor()
        return self._table_extractor
    
    @property
    def entity_extractor(self):
        """Ленивая инициализация экстрактора сущностей"""
        if self._entity_extractor is None:
            logger.info("Инициализация экстрактора сущностей")
            self._entity_extractor = EntityExtractor()
        return self._entity_extractor
    
    @property
    def form_extractor(self):
        """Ленивая инициализация экстрактора форм"""
        if self._form_extractor is None:
            logger.info("Инициализация экстрактора форм")
            self._form_extractor = FormExtractor()
        return self._form_extractor
    
    def extract_text(self, page_numbers=None):
        """
        Извлечение текста из PDF.
        
        Args:
            page_numbers (list): Список номеров страниц для обработки.
                              Если None, обрабатываются все страницы.
        
        Returns:
            dict: Словарь {номер_страницы: текст}
        """
        logger.info("Извлечение текста из PDF")
        self.extracted_text = self.pdf_processor.extract_text(page_numbers)
        return self.extracted_text
    
    def analyze_layout(self, page_numbers=None):
        """
        Анализ макета страниц PDF.
        
        Args:
            page_numbers (list): Список номеров страниц для обработки.
                              Если None, обрабатываются все страницы.
                              
        Returns:
            dict: Словарь {номер_страницы: макет}
        """
        logger.info("Анализ макета PDF")
        
        if not self.pdf_processor.document:
            logger.error("PDF-документ не загружен")
            return {}
            
        if page_numbers is None:
            page_numbers = range(len(self.pdf_processor.document))
            
        result = {}
        for page_num in page_numbers:
            if page_num >= len(self.pdf_processor.document):
                logger.warning(f"Страница {page_num} не существует")
                continue
                
            page = self.pdf_processor.document[page_num]
            layout = self.layout_extractor.extract_layout(page)
            result[page_num] = layout
            
        self.layout_results = result
        return result
    
    def extract_tables(self, page_numbers=None):
        """
        Извлечение таблиц из PDF.
        
        Args:
            page_numbers (list): Список номеров страниц для обработки.
                              Если None, обрабатываются все страницы.
                              
        Returns:
            dict: Словарь {номер_страницы: список_таблиц}
        """
        logger.info("Извлечение таблиц из PDF")
        
        # Если макет не был проанализирован, извлекаем таблицы напрямую
        if not self.layout_results:
            if page_numbers is None:
                pages_str = "all"
            else:
                pages_str = ",".join(map(str, page_numbers))
                
            self.table_results = self.table_extractor.extract_tables(
                self.pdf_path, 
                pages=pages_str
            )
            return self.table_results
        
        # Если макет был проанализирован, используем информацию о расположении таблиц
        table_regions = {}
        for page_num, layout in self.layout_results.items():
            if page_numbers is not None and page_num not in page_numbers:
                continue
                
            if layout["tables"]:
                table_regions[page_num] = []
                for table in layout["tables"]:
                    coords = table["coords"]
                    # Формат для camelot: [x1, y1, x2, y2]
                    table_regions[page_num].append([
                        coords["x1"], coords["y1"], coords["x2"], coords["y2"]
                    ])
        
        if table_regions:
            self.table_results = self.table_extractor.extract_tables_from_regions(
                self.pdf_path, 
                table_regions
            )
        else:
            self.table_results = {}
            
        return self.table_results
    
    def extract_entities(self, page_numbers=None):
        """
        Извлечение именованных сущностей из текста PDF.
        
        Args:
            page_numbers (list): Список номеров страниц для обработки.
                              Если None, обрабатываются все страницы.
                              
        Returns:
            dict: Словарь {номер_страницы: список_сущностей}
        """
        logger.info("Извлечение именованных сущностей из PDF")
        
        # Если текст еще не был извлечен
        if not self.extracted_text:
            self.extract_text(page_numbers)
            
        # Фильтруем страницы, если указан список
        if self.extracted_text is None:
            text_dict = {}
        elif page_numbers is not None:
            text_dict = {page: text for page, text in self.extracted_text.items() 
                        if page in page_numbers}
        else:
            text_dict = self.extracted_text
            
        self.entity_results = self.entity_extractor.extract_entities_from_pdf_text(text_dict)
        return self.entity_results
    
    def extract_form_fields(self, page_numbers=None):
        """
        Извлечение полей формы из PDF.
        
        Args:
            page_numbers (list): Список номеров страниц для обработки.
                              Если None, обрабатываются все страницы.
                              
        Returns:
            dict: Словарь {номер_страницы: список_полей}
        """
        logger.info("Извлечение полей формы из PDF")
        self.form_results = self.form_extractor.extract_form_fields(
            self.pdf_path, 
            page_numbers
        )
        return self.form_results
    
    def analyze_all(self, page_numbers=None):
        """
        Полный анализ PDF-документа.
        
        Args:
            page_numbers (list): Список номеров страниц для обработки.
                              Если None, обрабатываются все страницы.
                              
        Returns:
            dict: Результаты анализа
        """
        logger.info("Запуск полного анализа PDF")
        
        self.extract_text(page_numbers)
        self.analyze_layout(page_numbers)
        self.extract_tables(page_numbers)
        self.extract_entities(page_numbers)
        self.extract_form_fields(page_numbers)
        
        return {
            "text": self.extracted_text,
            "layout": self.layout_results,
            "tables": self.table_results,
            "entities": self.entity_results,
            "form_fields": self.form_results
        }
    
    def save_results(self, output_dir, save_tables=True):
        """
        Сохранение результатов анализа в указанную директорию.
        
        Args:
            output_dir (str): Путь для сохранения результатов
            save_tables (bool): Сохранять ли таблицы в CSV-файлы
            
        Returns:
            str: Путь к сохраненным результатам
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Создаем поддиректорию с временной меткой
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.basename(self.pdf_path).replace('.pdf', '')
        result_dir = os.path.join(output_dir, f"{filename}_{timestamp}")
        os.makedirs(result_dir, exist_ok=True)
        
        logger.info(f"Сохранение результатов анализа в {result_dir}")
        
        # Сохраняем извлеченный текст
        if self.extracted_text:
            text_file = os.path.join(result_dir, "extracted_text.json")
            with open(text_file, 'w', encoding='utf-8') as f:
                json.dump(self.extracted_text, f, ensure_ascii=False, indent=2)
        
        # Сохраняем результаты анализа макета
        if self.layout_results:
            layout_file = os.path.join(result_dir, "layout_results.json")
            with open(layout_file, 'w', encoding='utf-8') as f:
                json.dump(self.layout_results, f, ensure_ascii=False, indent=2)
        
        # Сохраняем именованные сущности
        if self.entity_results:
            entities_file = os.path.join(result_dir, "entity_results.json")
            with open(entities_file, 'w', encoding='utf-8') as f:
                json.dump(self.entity_results, f, ensure_ascii=False, indent=2)
        
        # Сохраняем поля формы
        if self.form_results:
            forms_file = os.path.join(result_dir, "form_results.json")
            with open(forms_file, 'w', encoding='utf-8') as f:
                json.dump(self.form_results, f, ensure_ascii=False, indent=2)
        
        # Сохраняем таблицы в CSV-файлы
        if self.table_results and save_tables:
            tables_dir = os.path.join(result_dir, "tables")
            os.makedirs(tables_dir, exist_ok=True)
            
            self.table_extractor.tables_to_csv(self.table_results, tables_dir)
        
        return result_dir
        
    def close(self):
        """Закрытие PDF-документа и освобождение ресурсов"""
        self.pdf_processor.close()
        logger.info("Анализатор PDF закрыт")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 