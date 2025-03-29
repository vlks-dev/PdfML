"""
Базовый класс для обработки PDF-документов
"""

import os
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import pytesseract
from pdf2image.pdf2image import convert_from_path

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """
    Базовый класс для обработки PDF-файлов.
    Поддерживает извлечение текста из обычных и отсканированных PDF-документов.
    """
    
    def __init__(self, pdf_path, use_ocr=False, ocr_lang='rus+eng'):
        """
        Инициализация обработчика PDF.
        
        Args:
            pdf_path (str): Путь к PDF-файлу
            use_ocr (bool): Использовать ли OCR для извлечения текста
            ocr_lang (str): Языки для OCR (формат Tesseract)
        """
        self.pdf_path = pdf_path
        self.use_ocr = use_ocr
        self.ocr_lang = ocr_lang
        self.document = None
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
            
        try:
            self.document = fitz.Document(pdf_path)
            logger.info(f"Загружен PDF с {len(self.document)} страницами")
        except Exception as e:
            logger.error(f"Ошибка при открытии PDF: {e}")
            raise
            
    def extract_text(self, page_numbers=None) -> dict[int, str]:
        """
        Извлечение текста из PDF.
        
        Args:
            page_numbers (list): Список номеров страниц для обработки.
                                Если None, обрабатываются все страницы.
        
        Returns:
            dict: Словарь {номер_страницы: текст}
        """
        if self.document is None:
            logger.error("PDF-документ не загружен")
            return {}
        
        if page_numbers is None:
            page_numbers = range(len(self.document))
            
        result = {}
        
        for page_num in page_numbers:
            if page_num >= len(self.document):
                logger.warning(f"Страница {page_num} не существует")
                continue
                
            page = self.document[page_num]
            
            if self.use_ocr:
                text = self._extract_text_with_ocr(page_num)
            else:
                text = page.get_textpage().extractText()
                
            if not text.strip() and not self.use_ocr:
                # Если извлечь текст не удалось, попробуем OCR
                logger.info(f"Страница {page_num} не содержит текста, пробуем OCR")
                text = self._extract_text_with_ocr(page_num)
                
            result[page_num] = text
            
        return result
    
    def _extract_text_with_ocr(self, page_num):
        """
        Извлечение текста с использованием OCR.
        
        Args:
            page_num (int): Номер страницы
            
        Returns:
            str: Извлеченный текст
        """
        # Конвертируем страницу в изображение
        pil_images = convert_from_path(
            self.pdf_path, 
            first_page=page_num+1, 
            last_page=page_num+1,
            dpi=300
        )
        
        if not pil_images:
            logger.error(f"Не удалось конвертировать страницу {page_num} в изображение")
            return ""
        
        img = pil_images[0]
        
        # Применяем OCR
        try:
            text = pytesseract.image_to_string(img, lang=self.ocr_lang)
            return text
        except Exception as e:
            logger.error(f"Ошибка OCR: {e}")
            return ""
    
    def close(self):
        """Закрытие документа и освобождение ресурсов"""
        if self.document:
            self.document.close()
            logger.info("PDF-документ закрыт")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 